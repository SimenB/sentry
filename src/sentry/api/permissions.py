from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from rest_framework.permissions import SAFE_METHODS, BasePermission, IsAuthenticated  # noqa: S012
from rest_framework.request import Request

from sentry.api.exceptions import (
    MemberDisabledOverLimit,
    SsoRequired,
    SuperuserRequired,
    TwoFactorRequired,
)
from sentry.auth import access
from sentry.auth.staff import has_staff_option, is_active_staff
from sentry.auth.superuser import SUPERUSER_ORG_ID, is_active_superuser
from sentry.auth.system import is_system_auth
from sentry.demo_mode.utils import get_readonly_scopes, is_demo_mode_enabled, is_demo_user
from sentry.hybridcloud.rpc import extract_id_from
from sentry.models.orgauthtoken import is_org_auth_token_auth, update_org_auth_token_last_used
from sentry.organizations.services.organization import (
    RpcOrganization,
    RpcUserOrganizationContext,
    organization_service,
)
from sentry.utils import auth

if TYPE_CHECKING:
    from rest_framework.views import APIView

    from sentry.models.organization import Organization


class RelayPermission(BasePermission):
    def has_permission(self, request: Request, view: object) -> bool:
        return getattr(request, "relay", None) is not None


class SystemPermission(BasePermission):
    def has_permission(self, request: Request, view: object) -> bool:
        return is_system_auth(request.auth)


class NoPermission(BasePermission):
    def has_permission(self, request: Request, view: object) -> bool:
        return False


class SuperuserPermission(BasePermission):
    """
    This permission class is used for endpoints that should ONLY be accessible
    by superuser.
    """

    def has_permission(self, request: Request, view: object) -> bool:
        return is_active_superuser(request)


class StaffPermission(BasePermission):
    """
    This permission class is used for endpoints that should ONLY be accessible
    by staff.
    """

    def has_permission(self, request: Request, view: object) -> bool:
        return is_active_staff(request)


# NOTE(schew2381): This is a temporary permission that does NOT perform an OR
# between SuperuserPermission and StaffPermission. Instead, it uses StaffPermission
# if the option is enabled for the user, and otherwise checks SuperuserPermission. We
# need this to handle the transition for endpoints that will only be accessible to
# staff but not superuser, that currently use SuperuserPermission. Once staff is
# released to the everyone, we can delete this permission and use StaffPermission
class SuperuserOrStaffFeatureFlaggedPermission(BasePermission):
    def has_permission(self, request: Request, view: object) -> bool:
        enforce_staff_permission = has_staff_option(request.user)

        if enforce_staff_permission:
            return StaffPermission().has_permission(request, view)

        return SuperuserPermission().has_permission(request, view)


class ScopedPermission(BasePermission):
    """
    Permissions work depending on the type of authentication:

    - A user inherits permissions based on their membership role. These are
      still dictated as common scopes, but they can't be checked until the
      has_object_permission hook is called.
    - ProjectKeys (legacy) are granted only project based scopes. This
    - APIKeys specify their scope, and work as expected.
    """

    scope_map: dict[str, Sequence[str]] = {
        "HEAD": (),
        "GET": (),
        "POST": (),
        "PUT": (),
        "PATCH": (),
        "DELETE": (),
    }

    def has_permission(self, request: Request, view: APIView) -> bool:
        # session-based auth has all scopes for a logged in user
        if not request.auth:
            return request.user.is_authenticated

        if is_org_auth_token_auth(request.auth):
            # Ensure we always update the last used date for the org auth token.
            # At this point, we don't have the projects yet, so we only update the org auth token's
            # last used date, clearing the project_last_used_id. We call this method again in endpoints
            # where a project is available to update the project_last_used_id.
            update_org_auth_token_last_used(request.auth, [])

        assert request.method is not None
        allowed_scopes = set(self.scope_map.get(request.method, []))
        current_scopes = request.auth.get_scopes()
        return any(s in allowed_scopes for s in current_scopes)

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        return False


class SentryPermission(ScopedPermission):
    def is_not_2fa_compliant(
        self, request: Request, organization: RpcOrganization | Organization
    ) -> bool:
        return False

    def needs_sso(self, request: Request, organization: Organization | RpcOrganization) -> bool:
        return False

    def is_member_disabled_from_limit(
        self,
        request: Request,
        organization: RpcUserOrganizationContext | RpcOrganization | Organization,
    ) -> bool:
        return False

    # This wide typing on organization gives us a lot of flexibility as we move forward with hybrid cloud.
    # Once we have fully encircled all call sites (which are MANY!) we can collapse the typing around a single
    # usage (likely the RpcUserOrganizationContext, which is necessary for access and organization details).
    # For now, this wide typing allows incremental rollout of those changes.  Be mindful how you use
    # organization in this method to stay compatible with all 3 paths.
    def determine_access(
        self,
        request: Request,
        organization: RpcUserOrganizationContext | Organization | RpcOrganization,
    ) -> None:
        from sentry.api.base import logger

        user_id = request.user.id if request.user else None
        org_context: RpcUserOrganizationContext | None
        if isinstance(organization, RpcUserOrganizationContext):
            org_context = organization
        else:
            org_context = organization_service.get_organization_by_id(
                id=extract_id_from(organization), user_id=user_id
            )

        if org_context is None:
            assert False, "Failed to fetch organization in determine_access"

        organization = org_context.organization
        extra = {"organization_id": organization.id, "user_id": user_id}

        if request.auth:
            if request.user and request.user.is_authenticated:
                request.access = access.from_request_org_and_scopes(
                    request=request,
                    rpc_user_org_context=org_context,
                    scopes=request.auth.get_scopes(),
                )
            else:
                request.access = access.from_rpc_auth(
                    auth=request.auth, rpc_user_org_context=org_context
                )

            if org_context.member and self.is_not_2fa_compliant(request, organization):
                logger.info(
                    "access.not-2fa-compliant.auth-token",
                    extra=extra,
                )
                raise TwoFactorRequired()

            if self.is_member_disabled_from_limit(request, org_context):
                logger.info(
                    "access.member-disabled-from-limit",
                    extra=extra,
                )
                raise MemberDisabledOverLimit(organization)

            return

        request.access = access.from_request_org_and_scopes(
            request=request,
            rpc_user_org_context=org_context,
        )

        if auth.is_user_signed_request(request):
            # if the user comes from a signed request
            # we let them pass if sso is enabled
            logger.info(
                "access.signed-sso-passthrough",
                extra=extra,
            )
        elif request.user.is_authenticated:
            # session auth needs to confirm various permissions
            if self.needs_sso(request, organization):
                logger.info(
                    "access.must-sso",
                    extra=extra,
                )

                after_login_redirect = request.META.get("HTTP_REFERER", "")
                if not auth.is_valid_redirect(
                    after_login_redirect, allowed_hosts=(request.get_host(),)
                ):
                    after_login_redirect = None

                raise SsoRequired(
                    organization=organization,
                    request=request,
                    after_login_redirect=after_login_redirect,
                )

            if self.is_not_2fa_compliant(request, organization):
                logger.info(
                    "access.not-2fa-compliant",
                    extra=extra,
                )
                if request.user.is_superuser and extract_id_from(organization) != SUPERUSER_ORG_ID:
                    raise SuperuserRequired()

                raise TwoFactorRequired()

            if self.is_member_disabled_from_limit(request, org_context):
                logger.info(
                    "access.member-disabled-from-limit",
                    extra=extra,
                )
                raise MemberDisabledOverLimit(organization)


class StaffPermissionMixin(SentryPermission):
    """
    Sentry endpoints that should be accessible by staff but have an existing permission
    class (that is not StaffPermission) require this mixin because staff does not give
    any scopes.
    NOTE: This mixin MUST be the leftmost parent class in the child class declaration in
    order to work properly. See 'OrganizationAndStaffPermission' for an example of this or
    https://www.python.org/download/releases/2.3/mro/ to learn more.
    """

    staff_allowed_methods = {"GET", "POST", "PUT", "DELETE"}

    def has_permission(self, request: Request, view: APIView) -> bool:
        """
        Calls the parent class's has_permission method. If it returns False or
        raises an exception and the method is allowed by the mixin, we then check
        if the request is from an active staff. Raised exceptions are not caught
        if the request is not allowed by the mixin or from an active staff.
        """
        try:
            if super().has_permission(request, view):
                return True
        except Exception:
            if not (request.method in self.staff_allowed_methods and is_active_staff(request)):
                raise
            return True
        return request.method in self.staff_allowed_methods and is_active_staff(request)

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        """
        Calls the parent class's has_object_permission method. If it returns False or
        raises an exception and the method is allowed by the mixin, we then check
        if the request is from an active staff. Raised exceptions are not caught
        if the request is not allowed by the mixin or from an active staff.
        """
        try:
            if super().has_object_permission(request, view, obj):
                return True
        except Exception:
            if not (request.method in self.staff_allowed_methods and is_active_staff(request)):
                raise
            return True
        return request.method in self.staff_allowed_methods and is_active_staff(request)

    def is_not_2fa_compliant(
        self, request: Request, organization: RpcOrganization | Organization
    ) -> bool:
        return super().is_not_2fa_compliant(request, organization) and not is_active_staff(request)


class DemoSafePermission(SentryPermission):
    """
    A permission class that extends `SentryPermission` to provide read-only access for users
    in a demo mode. This class modifies the access control logic to ensure that users identified
    as read-only can only perform safe operations, such as GET and HEAD requests, on resources.
    """

    def determine_access(
        self,
        request: Request,
        organization: RpcUserOrganizationContext | Organization | RpcOrganization,
    ) -> None:
        if not is_demo_user(request.user):
            return super().determine_access(request, organization)

        org_context: RpcUserOrganizationContext | None = None
        if isinstance(organization, RpcUserOrganizationContext):
            org_context = organization
        else:
            org_context = organization_service.get_organization_by_id(
                id=extract_id_from(organization),
                user_id=request.user.id if request.user else None,
            )

        assert org_context is not None, "Failed to fetch organization in determine_access"

        if org_context.member and is_demo_mode_enabled():
            readonly_scopes = get_readonly_scopes()
            org_context.member.scopes = sorted(readonly_scopes)
            request.access = access.from_request_org_and_scopes(
                request=request,
                rpc_user_org_context=org_context,
                scopes=readonly_scopes,
            )

    def has_permission(self, request: Request, view: APIView) -> bool:
        if is_demo_user(request.user):
            if not is_demo_mode_enabled() or request.method not in SAFE_METHODS:
                return False

        return super().has_permission(request, view)

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        if is_demo_user(request.user):
            if not is_demo_mode_enabled() or request.method not in SAFE_METHODS:
                return False

        return super().has_object_permission(request, view, obj)


class SentryIsAuthenticated(IsAuthenticated):
    """
    Used to deny access for demo users in both view and object permission checks.
    """

    def has_permission(self, request: Request, view: APIView) -> bool:
        if is_demo_user(request.user):
            return False

        return super().has_permission(request, view)

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        if is_demo_user(request.user):
            return False

        return super().has_object_permission(request, view, obj)
