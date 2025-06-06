from __future__ import annotations

import datetime
import logging
import secrets
from collections import defaultdict
from collections.abc import Mapping
from datetime import timedelta
from enum import Enum
from hashlib import md5
from typing import TYPE_CHECKING, Any, ClassVar, TypedDict
from urllib.parse import urlencode

from django.conf import settings
from django.db import models, router, transaction
from django.db.models import Q, QuerySet
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.translation import gettext_lazy as _
from structlog import get_logger

from bitfield.models import typed_dict_bitfield
from sentry import features, roles
from sentry.backup.dependencies import NormalizedModelName, PrimaryKeyMap
from sentry.backup.helpers import ImportFlags
from sentry.backup.scopes import ImportScope, RelocationScope
from sentry.db.models import (
    BoundedPositiveIntegerField,
    FlexibleForeignKey,
    region_silo_model,
    sane_repr,
)
from sentry.db.models.fields.hybrid_cloud_foreign_key import HybridCloudForeignKey
from sentry.db.models.manager.base import BaseManager
from sentry.db.postgres.transactions import in_test_hide_transaction_boundary
from sentry.exceptions import UnableToAcceptMemberInvitationException
from sentry.hybridcloud.models.outbox import outbox_context
from sentry.hybridcloud.outbox.base import ReplicatedRegionModel
from sentry.hybridcloud.outbox.category import OutboxCategory
from sentry.hybridcloud.rpc import extract_id_from
from sentry.hybridcloud.services.organizationmember_mapping import (
    RpcOrganizationMemberMappingUpdate,
    organizationmember_mapping_service,
)
from sentry.models.organizationmemberinvite import OrganizationMemberInvite
from sentry.models.team import TeamStatus
from sentry.roles import organization_roles
from sentry.roles.manager import OrganizationRole
from sentry.signals import member_invited
from sentry.users.services.user import RpcUser
from sentry.users.services.user.service import user_service
from sentry.utils.http import absolute_uri

if TYPE_CHECKING:
    from sentry.integrations.services.integration import RpcIntegration
    from sentry.models.organization import Organization

_OrganizationMemberFlags = TypedDict(
    "_OrganizationMemberFlags",
    {
        "sso:linked": bool,
        "sso:invalid": bool,
        "member-limit:restricted": bool,
        "idp:provisioned": bool,
        "idp:role-restricted": bool,
        "partnership:restricted": bool,
    },
)

logger = logging.getLogger("sentry.org_roles")


INVITE_DAYS_VALID = 30


class InviteStatus(Enum):
    APPROVED = 0
    REQUESTED_TO_BE_INVITED = 1
    REQUESTED_TO_JOIN = 2

    @classmethod
    def as_choices(cls):
        return (
            (InviteStatus.APPROVED.value, _("Approved")),
            (
                InviteStatus.REQUESTED_TO_BE_INVITED.value,
                _("Organization member requested to invite user"),
            ),
            (InviteStatus.REQUESTED_TO_JOIN.value, _("User requested to join organization")),
        )


invite_status_names = {
    InviteStatus.APPROVED.value: "approved",
    InviteStatus.REQUESTED_TO_BE_INVITED.value: "requested_to_be_invited",
    InviteStatus.REQUESTED_TO_JOIN.value: "requested_to_join",
}


ERR_CANNOT_INVITE = "Your organization is not allowed to invite members."
ERR_JOIN_REQUESTS_DISABLED = "Your organization does not allow requests to join."


class OrganizationMemberManager(BaseManager["OrganizationMember"]):
    def get_contactable_members_for_org(self, organization_id: int) -> QuerySet:
        """Get a list of members we can contact for an organization through email."""
        # TODO(Steve): check member-limit:restricted
        return self.filter(
            organization_id=organization_id,
            invite_status=InviteStatus.APPROVED.value,
            user_id__isnull=False,
        )

    def delete_expired(self, threshold: datetime.datetime) -> None:
        """Delete un-accepted member invitations that expired `threshold` days ago."""
        from sentry.auth.services.auth import auth_service

        orgs_with_scim = auth_service.get_org_ids_with_scim()
        for member in (
            self.filter(
                token_expires_at__lt=threshold,
                user_id__exact=None,
            )
            .exclude(email__exact=None)
            .exclude(organization_id__in=orgs_with_scim)
        ):
            member.delete()

    def get_for_integration(
        self, integration: RpcIntegration | int, user: RpcUser, organization_id: int | None = None
    ) -> QuerySet[OrganizationMember]:
        # This can be moved into the integration service once OrgMemberMapping is completed.
        # We are forced to do an ORM -> service -> ORM call to reduce query size while avoiding
        # cross silo queries until we have a control silo side to map users through.
        from sentry.integrations.services.integration import integration_service

        if organization_id is not None:
            if (
                integration_service.get_organization_integration(
                    integration_id=extract_id_from(integration), organization_id=organization_id
                )
                is None
            ):
                return self.filter(Q())
            return self.filter(organization_id=organization_id, user_id=user.id)

        org_ids = list(self.filter(user_id=user.id).values_list("organization_id", flat=True))
        org_ids = [
            oi.organization_id
            for oi in integration_service.get_organization_integrations(
                organization_ids=org_ids, integration_id=extract_id_from(integration)
            )
        ]
        return self.filter(user_id=user.id, organization_id__in=org_ids).select_related(
            "organization"
        )

    def get_member_invite_query(self, id: int) -> QuerySet:
        return self.filter(
            invite_status__in=[
                InviteStatus.REQUESTED_TO_BE_INVITED.value,
                InviteStatus.REQUESTED_TO_JOIN.value,
            ],
            user_id__isnull=True,
            id=id,
        )

    def get_teams_by_user(self, organization: Organization) -> dict[int, list[int]]:
        queryset = self.filter(organization_id=organization.id).values_list("user_id", "teams")
        user_teams: dict[int, list[int]] = defaultdict(list)
        for user_id, team_id in queryset:
            if user_id is not None:
                user_teams[user_id].append(team_id)
        return user_teams

    def get_members_by_email_and_role(self, email: str, role: str) -> QuerySet:
        users_by_email = user_service.get_many(
            filter=dict(
                emails=[email],
                is_active=True,
            )
        )

        return self.filter(role=role, user_id__in=[u.id for u in users_by_email])


@region_silo_model
class OrganizationMember(ReplicatedRegionModel):
    """
    Identifies relationships between organizations and users.

    Users listed as team members are considered to have access to all projects
    and could be thought of as team owners (though their access level may not)
    be set to ownership.
    """

    __relocation_scope__ = RelocationScope.Organization
    category = OutboxCategory.ORGANIZATION_MEMBER_UPDATE

    objects: ClassVar[OrganizationMemberManager] = OrganizationMemberManager()

    organization = FlexibleForeignKey("sentry.Organization", related_name="member_set")

    user_id = HybridCloudForeignKey("sentry.User", on_delete="CASCADE", null=True, blank=True)
    # This email indicates the invite state of this membership -- it will be cleared when the user is set.
    # it does not necessarily represent the final email of the user associated with the membership, see user_email.
    email = models.EmailField(null=True, blank=True, max_length=75)
    role = models.CharField(max_length=32, default=str(organization_roles.get_default().id))

    flags = typed_dict_bitfield(_OrganizationMemberFlags, default=0)

    token = models.CharField(max_length=64, null=True, blank=True, unique=True)
    date_added = models.DateTimeField(default=timezone.now)
    token_expires_at = models.DateTimeField(default=None, null=True)
    has_global_access = models.BooleanField(default=True)
    teams = models.ManyToManyField(
        "sentry.Team", blank=True, through="sentry.OrganizationMemberTeam"
    )
    inviter_id = HybridCloudForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete="SET_NULL",
    )
    invite_status = models.PositiveSmallIntegerField(
        choices=InviteStatus.as_choices(),
        default=InviteStatus.APPROVED.value,
        null=True,
    )

    # Deprecated -- no longer used
    type = BoundedPositiveIntegerField(default=50, blank=True)

    # These attributes are replicated via USER_UPDATE category outboxes for the user object associated with the user_id
    # when it exists.
    user_is_active = models.BooleanField(null=False, default=True, db_default=True)
    # Note, this is the email of the user that may or may not be associated with the member, not the email used to
    # invite the user.
    user_email = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        app_label = "sentry"
        db_table = "sentry_organizationmember"
        unique_together = (("organization", "user_id"), ("organization", "email"))

    __repr__ = sane_repr("organization_id", "user_id", "email", "role")

    def save(self, *args, **kwargs):
        if self.id is not None:
            invite = OrganizationMemberInvite.objects.filter(organization_member_id=self.id).first()
            assert invite is None, "Cannot save placeholder organization member for an invited user"

        with outbox_context(transaction.atomic(using=router.db_for_write(OrganizationMember))):
            if self.token and not self.token_expires_at:
                self.refresh_expires_at()
            super().save(*args, **kwargs)

    def refresh_from_db(self, *args, **kwargs):
        super().refresh_from_db(*args, **kwargs)

    def set_user(self, user_id: int):
        self.user_id = user_id
        self.email = None
        self.token = None
        self.token_expires_at = None

    def remove_user(self):
        self.email = self.get_email()
        self.user_id = None
        self.token = self.generate_token()

    def regenerate_token(self):
        self.token = self.generate_token()
        self.refresh_expires_at()

    def payload_for_update(self) -> dict[str, Any] | None:
        return dict(user_id=self.user_id)

    def refresh_expires_at(self):
        now = timezone.now()
        self.token_expires_at = now + timedelta(days=INVITE_DAYS_VALID)

    def approve_invite(self):
        self.invite_status = InviteStatus.APPROVED.value
        self.regenerate_token()

    def get_invite_status_name(self):
        if self.invite_status is None:
            return
        return invite_status_names[self.invite_status]

    @property
    def invite_approved(self):
        return self.invite_status == InviteStatus.APPROVED.value

    @property
    def requested_to_join(self):
        return self.invite_status == InviteStatus.REQUESTED_TO_JOIN.value

    @property
    def requested_to_be_invited(self):
        return self.invite_status == InviteStatus.REQUESTED_TO_BE_INVITED.value

    @property
    def is_pending(self):
        return self.user_id is None

    @property
    def token_expired(self):
        # Old tokens don't expire to preserve compatibility and not require
        # a backfill migration.
        if self.token_expires_at is None:
            return False
        if self.token_expires_at > timezone.now():
            return False
        return True

    @property
    def legacy_token(self):
        email = self.get_email()
        if not email:
            return ""
        checksum = md5()
        checksum.update(str(self.organization_id).encode("utf-8"))
        checksum.update(email.encode("utf-8"))
        checksum.update(force_bytes(settings.SECRET_KEY))
        return checksum.hexdigest()

    def generate_token(self):
        return secrets.token_hex(nbytes=32)

    def get_invite_link(self, referrer: str | None = None):
        if not self.is_pending or not self.invite_approved:
            return None
        path = reverse(
            "sentry-accept-invite",
            kwargs={
                "member_id": self.id,
                "token": self.token or self.legacy_token,
            },
        )
        invite_link = self.organization.absolute_url(path)
        if referrer:
            invite_link += "?referrer=" + referrer
        return invite_link

    def send_invite_email(self, referrer: str | None = None):
        from sentry.utils.email import MessageBuilder

        context = {
            "email": self.email,
            "organization": self.organization,
            "url": self.get_invite_link(referrer),
        }

        msg = MessageBuilder(
            subject="Join %s in using Sentry" % self.organization.name,
            template="sentry/emails/member-invite.txt",
            html_template="sentry/emails/member-invite.html",
            type="organization.invite",
            context=context,
        )

        try:
            msg.send_async([self.get_email()])
        except Exception as e:
            mail_logger = get_logger(name="sentry.mail")
            mail_logger.exception(e)

    def send_sso_link_email(self, sending_user_email: str, provider):
        from sentry.utils.email import MessageBuilder

        link_args = {"organization_slug": self.organization.slug}
        context = {
            "organization": self.organization,
            "actor_email": sending_user_email,
            "provider": provider,
            "url": absolute_uri(reverse("sentry-auth-organization", kwargs=link_args)),
        }

        msg = MessageBuilder(
            subject=f"Action Required for {self.organization.name}",
            template="sentry/emails/auth-link-identity.txt",
            html_template="sentry/emails/auth-link-identity.html",
            type="organization.auth_link",
            context=context,
        )
        msg.send_async([self.get_email()])

    def send_sso_unlink_email(self, disabling_user: RpcUser | str, provider):
        from sentry.users.services.lost_password_hash import lost_password_hash_service
        from sentry.utils.email import MessageBuilder

        # Nothing to send if this member isn't associated to a user
        if not self.user_id:
            return

        email = self.get_email()
        recover_uri = "{path}?{query}".format(
            path=reverse("sentry-account-recover"), query=urlencode({"email": email})
        )
        user = user_service.get_user(user_id=self.user_id)
        if not user:
            return

        has_password = user.has_usable_password()
        actor_email = disabling_user
        if isinstance(disabling_user, RpcUser):
            actor_email = disabling_user.email

        context = {
            "email": email,
            "recover_url": absolute_uri(recover_uri),
            "has_password": has_password,
            "organization": self.organization,
            "actor_email": actor_email,
            "provider": provider,
        }

        if not has_password:
            password_hash = lost_password_hash_service.get_or_create(user_id=self.user_id)
            context["set_password_url"] = password_hash.get_absolute_url(mode="set_password")

        msg = MessageBuilder(
            subject=f"Action Required for {self.organization.name}",
            template="sentry/emails/auth-sso-disabled.txt",
            html_template="sentry/emails/auth-sso-disabled.html",
            type="organization.auth_sso_disabled",
            context=context,
        )
        msg.send_async([email])

    def get_display_name(self):
        if self.user_id:
            user = user_service.get_user(user_id=self.user_id)
            if user:
                return user.get_display_name()
        return self.email

    def get_label(self):
        if self.user_id:
            user = user_service.get_user(user_id=self.user_id)
            if user:
                return user.get_label()
        return self.email or self.id

    def get_email(self):
        if self.user_id:
            if self.user_email:
                return self.user_email

            # This is a fallback case when the org member outbox message from
            #  the control-silo has not been drained/denormalized, but we need
            #  to retrieve it, so we skip our rpc-in-transaction validations here.
            with in_test_hide_transaction_boundary():
                user = user_service.get_user(user_id=self.user_id)
            if user and user.email:
                return user.email
        return self.email or ""

    def get_avatar_type(self):
        if self.user_id:
            user = user_service.get_user(user_id=self.user_id)
            if user:
                return user.get_avatar_type()
        return "letter_avatar"

    def get_audit_log_data(self):
        from sentry.models.organizationmemberteam import OrganizationMemberTeam
        from sentry.models.team import Team

        teams = list(
            Team.objects.filter(
                id__in=OrganizationMemberTeam.objects.filter(
                    organizationmember=self, is_active=True
                ).values_list("team", flat=True)
            ).values("id", "slug")
        )

        return {
            "email": self.get_email(),
            "user": self.user_id,
            "teams": [t["id"] for t in teams],
            "teams_slugs": [t["slug"] for t in teams],
            "has_global_access": self.has_global_access,
            "role": self.role,
            "invite_status": (
                invite_status_names[self.invite_status] if self.invite_status is not None else None
            ),
        }

    def get_teams(self):
        from sentry.models.organizationmemberteam import OrganizationMemberTeam
        from sentry.models.team import Team

        return Team.objects.filter(
            status=TeamStatus.ACTIVE,
            id__in=OrganizationMemberTeam.objects.filter(
                organizationmember=self, is_active=True
            ).values("team"),
        )

    def get_team_roles(self):
        from sentry.models.organizationmemberteam import OrganizationMemberTeam

        return OrganizationMemberTeam.objects.filter(
            organizationmember=self, is_active=True
        ).values("team", "role")

    def get_scopes(self) -> frozenset[str]:
        # include org roles from team membership
        role = organization_roles.get(self.role)
        scopes = self.organization.get_scopes(role)

        return frozenset(scopes)

    def validate_invitation(self, user_to_approve, allowed_roles):
        """
        Validates whether an org has the options to invite members, handle join requests,
        and that the member role doesn't exceed the allowed roles to invite.
        """
        organization = self.organization
        if not features.has("organizations:invite-members", organization, actor=user_to_approve):
            raise UnableToAcceptMemberInvitationException(ERR_CANNOT_INVITE)

        if (
            organization.get_option("sentry:join_requests") is False
            and self.invite_status == InviteStatus.REQUESTED_TO_JOIN.value
        ):
            raise UnableToAcceptMemberInvitationException(ERR_JOIN_REQUESTS_DISABLED)

        # members cannot invite roles higher than their own
        if not {self.role} & {r.id for r in allowed_roles}:
            raise UnableToAcceptMemberInvitationException(
                f"You do not have permission to approve a member invitation with the role {self.role}."
            )
        return True

    def approve_member_invitation(
        self, user_to_approve, api_key=None, ip_address=None, referrer=None
    ):
        """
        Approve a member invite/join request and send an audit log entry
        """
        from sentry import audit_log
        from sentry.utils.audit import create_audit_entry_from_user

        with transaction.atomic(using=router.db_for_write(OrganizationMember)):
            self.approve_invite()
            self.save()

        if settings.SENTRY_ENABLE_INVITES:
            self.send_invite_email()
            member_invited.send_robust(
                member=self,
                user=user_to_approve,
                sender=self.approve_member_invitation,
                referrer=referrer,
            )

        create_audit_entry_from_user(
            user_to_approve,
            api_key,
            ip_address,
            organization_id=self.organization_id,
            target_object=self.id,
            data=self.get_audit_log_data(),
            event=(
                audit_log.get_event_id("MEMBER_INVITE")
                if settings.SENTRY_ENABLE_INVITES
                else audit_log.get_event_id("MEMBER_ADD")
            ),
        )

    def reject_member_invitation(
        self,
        user_to_approve,
        api_key=None,
        ip_address=None,
    ):
        """
        Reject a member invite/join request and send an audit log entry
        """
        from sentry import audit_log
        from sentry.utils.audit import create_audit_entry_from_user

        if self.invite_status == InviteStatus.APPROVED.value:
            return

        create_audit_entry_from_user(
            user_to_approve,
            api_key,
            ip_address,
            organization_id=self.organization_id,
            target_object=self.id,
            data=self.get_audit_log_data(),
            event=audit_log.get_event_id("INVITE_REQUEST_REMOVE"),
        )

        self.delete()

    def get_allowed_org_roles_to_invite(self) -> list[OrganizationRole]:
        """
        Return a list of org-level roles which that member could invite
        Must check if member member has member:admin first before checking
        """
        member_scopes = self.get_scopes()

        # NOTE: We must fetch scopes using self.organization.get_scopes(role) instead of r.scopes
        # because this accounts for the org option that allows/restricts members from having the
        # 'alerts:write' scope, which is given by default to the member role in the SENTRY_ROLES config.
        return [
            r
            for r in organization_roles.get_all()
            if self.organization.get_scopes(r).issubset(member_scopes)
        ]

    def is_only_owner(self) -> bool:
        if organization_roles.get_top_dog().id != self.role:
            return False

        # check if any other member has the owner role, including through a team
        is_only_owner = not (
            self.organization.get_members_with_org_roles(roles=[roles.get_top_dog().id])
            .exclude(id=self.id)
            .exists()
        )
        return is_only_owner

    @classmethod
    def handle_async_deletion(
        cls, identifier: int, shard_identifier: int, payload: Mapping[str, Any] | None
    ) -> None:
        from sentry.identity.services.identity import identity_service

        if payload and payload.get("user_id") is not None:
            identity_service.delete_identities(
                user_id=payload["user_id"], organization_id=shard_identifier
            )
        organizationmember_mapping_service.delete(
            organizationmember_id=identifier,
            organization_id=shard_identifier,
        )

    def handle_async_replication(self, shard_identifier: int) -> None:
        rpc_org_member_update = RpcOrganizationMemberMappingUpdate.from_orm(self)

        organizationmember_mapping_service.upsert_mapping(
            organizationmember_id=self.id,
            organization_id=shard_identifier,
            mapping=rpc_org_member_update,
        )

    @classmethod
    def query_for_relocation_export(cls, q: Q, pk_map: PrimaryKeyMap) -> Q:
        q = super().query_for_relocation_export(q, pk_map)

        # Manually avoid filtering on `inviter_id` when exporting. This ensures that
        # `OrganizationMember`s that were invited by a user from a different organization are not
        # filtered out when export in `Organization` scope.
        new_q = Q()
        for clause in q.children:
            if not isinstance(clause, Q):
                new_q.children.append(clause)
                continue

            mentioned_inviter = False
            for subclause in clause.children:
                if isinstance(subclause, tuple) and "inviter" in subclause[0]:
                    mentioned_inviter = True
                    break
            if not mentioned_inviter:
                new_q.children.append(clause)

        return new_q

    def normalize_before_relocation_import(
        self, pk_map: PrimaryKeyMap, scope: ImportScope, flags: ImportFlags
    ) -> int | None:
        # If the inviter didn't make it into the import, just null them out rather than evicting
        # this user from the organization due to their absence.
        if (
            self.inviter_id is not None
            and pk_map.get_pk(NormalizedModelName("sentry.user"), self.inviter_id) is None
        ):
            self.inviter_id = None

        # If there is a token collision, just wipe the token. The user can always make a new one.
        matching_token = self.__class__.objects.filter(token=self.token).first()
        if matching_token is not None:
            self.token = None
            self.token_expires_at = None

        return super().normalize_before_relocation_import(pk_map, scope, flags)
