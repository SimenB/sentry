from __future__ import annotations

import logging
import zoneinfo
from collections.abc import Iterable, Mapping, MutableMapping
from datetime import UTC, tzinfo
from typing import Any

import sentry_sdk

from sentry import analytics, features
from sentry.analytics.events.alert_sent import AlertSentEvent
from sentry.db.models import Model
from sentry.eventstore.models import GroupEvent
from sentry.integrations.issue_alert_image_builder import IssueAlertImageBuilder
from sentry.integrations.types import (
    ExternalProviderEnum,
    ExternalProviders,
    IntegrationProviderSlug,
)
from sentry.issues.grouptype import (
    GROUP_CATEGORIES_CUSTOM_EMAIL,
    GroupCategory,
    PerformanceP95EndpointRegressionGroupType,
    ProfileFunctionRegressionType,
)
from sentry.models.group import Group
from sentry.notifications.notifications.base import ProjectNotification
from sentry.notifications.types import (
    ActionTargetType,
    FallthroughChoiceType,
    NotificationSettingEnum,
)
from sentry.notifications.utils import (
    get_commits,
    get_generic_data,
    get_interface_list,
    get_performance_issue_alert_subtitle,
    get_replay_id,
    get_transaction_data,
    has_alert_integration,
    has_integrations,
)
from sentry.notifications.utils.links import (
    create_link_to_workflow,
    get_group_settings_link,
    get_integration_link,
    get_issue_replay_link,
    get_rules,
    get_snooze_url,
)
from sentry.notifications.utils.participants import get_owner_reason, get_send_to
from sentry.notifications.utils.rules import get_key_from_rule_data
from sentry.plugins.base.structs import Notification
from sentry.types.actor import Actor
from sentry.types.group import GroupSubStatus
from sentry.users.services.user_option import user_option_service
from sentry.users.services.user_option.service import get_option_from_list
from sentry.utils import metrics
from sentry.utils.http import absolute_uri

logger = logging.getLogger(__name__)


def get_group_substatus_text(group: Group) -> str:
    if group.substatus == GroupSubStatus.NEW:
        return "New issue"
    elif group.substatus == GroupSubStatus.REGRESSED:
        return "Regressed issue"
    elif group.substatus == GroupSubStatus.ONGOING:
        return "Ongoing issue"
    return "New Alert"


GENERIC_TEMPLATE_NAME = "generic"


class AlertRuleNotification(ProjectNotification):
    message_builder = "IssueNotificationMessageBuilder"
    metrics_key = "issue_alert"
    notification_setting_type_enum = NotificationSettingEnum.ISSUE_ALERTS
    template_path = "sentry/emails/error"

    def __init__(
        self,
        notification: Notification,
        target_type: ActionTargetType,
        target_identifier: int | None = None,
        fallthrough_choice: FallthroughChoiceType | None = None,
        notification_uuid: str | None = None,
    ) -> None:
        event = notification.event
        group = event.group
        project = group.project
        super().__init__(project, notification_uuid)
        self.group = group
        self.event = event
        self.target_type = target_type
        self.target_identifier = target_identifier
        self.fallthrough_choice = fallthrough_choice
        self.rules = notification.rules

        if event.group.issue_category in GROUP_CATEGORIES_CUSTOM_EMAIL:
            # profile issues use the generic template for now
            if (
                isinstance(event, GroupEvent)
                and event.occurrence
                and event.occurrence.evidence_data.get("template_name") == "profile"
            ):
                email_template_name = GENERIC_TEMPLATE_NAME
            else:
                email_template_name = event.group.issue_category.name.lower()
        else:
            email_template_name = GENERIC_TEMPLATE_NAME

        self.template_path = f"sentry/emails/{email_template_name}"

    def get_participants(self) -> Mapping[ExternalProviders, Iterable[Actor]]:
        return get_send_to(
            project=self.project,
            target_type=self.target_type,
            target_identifier=self.target_identifier,
            event=self.event,
            notification_type_enum=self.notification_setting_type_enum,
            fallthrough_choice=self.fallthrough_choice,
            rules=self.rules,
            notification_uuid=self.notification_uuid,
        )

    def get_subject(self, context: Mapping[str, Any] | None = None) -> str:
        return str(self.event.get_email_subject())

    @property
    def reference(self) -> Model | None:
        return self.group

    def get_recipient_context(
        self, recipient: Actor, extra_context: Mapping[str, Any]
    ) -> MutableMapping[str, Any]:
        tz: tzinfo = UTC
        if recipient.is_user:
            user_options = user_option_service.get_many(
                filter={"user_ids": [recipient.id], "keys": ["timezone"]}
            )
            user_tz = get_option_from_list(user_options, key="timezone", default="UTC")
            try:
                tz = zoneinfo.ZoneInfo(user_tz)
            except (ValueError, zoneinfo.ZoneInfoNotFoundError):
                pass
        return {
            **super().get_recipient_context(recipient, extra_context),
            "timezone": tz,
        }

    def get_image_url(self) -> str | None:
        image_builder = IssueAlertImageBuilder(
            group=self.group, provider=ExternalProviderEnum.EMAIL
        )
        return image_builder.get_image_url()

    def is_new_design(self) -> bool:
        return self.group.issue_type in [
            PerformanceP95EndpointRegressionGroupType,
            ProfileFunctionRegressionType,
        ]

    def get_context(self) -> MutableMapping[str, Any]:
        environment = self.event.get_tag("environment")
        enhanced_privacy = self.organization.flags.enhanced_privacy
        rule_details = get_rules(self.rules, self.organization, self.project, self.group.type)
        sentry_query_params = self.get_sentry_query_params(ExternalProviders.EMAIL)
        for rule in rule_details:
            rule.url = rule.url + sentry_query_params
            rule.status_url = rule.url + sentry_query_params

        notification_reason = get_owner_reason(
            project=self.project,
            target_type=self.target_type,
            event=self.event,
            fallthrough_choice=self.fallthrough_choice,
        )
        fallback_params: MutableMapping[str, str] = {}
        group_header = get_group_substatus_text(self.group)

        notification_uuid = self.notification_uuid if hasattr(self, "notification_uuid") else None
        context = {
            "project_label": self.project.get_full_name(),
            "group": self.group,
            "group_header": group_header,
            "event": self.event,
            "link": get_group_settings_link(
                self.group,
                environment,
                rule_details,
                None,
                notification_uuid=notification_uuid,
                **fallback_params,
            ),
            "rules": rule_details,
            "has_integrations": has_integrations(self.organization, self.project),
            "enhanced_privacy": enhanced_privacy,
            "commits": get_commits(self.project, self.event),
            "environment": environment,
            "slack_link": get_integration_link(
                self.organization, IntegrationProviderSlug.SLACK.value, self.notification_uuid
            ),
            "notification_reason": notification_reason,
            "notification_settings_link": absolute_uri(
                f"/settings/account/notifications/alerts/{sentry_query_params}"
            ),
            "has_alert_integration": has_alert_integration(self.project),
            "issue_type": self.group.issue_type.description,
            "subtitle": self.event.title,
            "chart_image": self.get_image_url(),
            "is_new_design": self.is_new_design(),
        }

        # if the organization has enabled enhanced privacy controls we don't send
        # data which may show PII or source code
        if not enhanced_privacy:
            context.update({"tags": self.event.tags, "interfaces": get_interface_list(self.event)})

        has_session_replay = features.has("organizations:session-replay", self.organization)
        show_replay_link = features.has(
            "organizations:session-replay-issue-emails", self.organization
        )
        if has_session_replay and show_replay_link and get_replay_id(self.event):
            context.update(
                {
                    "issue_replays_url": get_issue_replay_link(self.group, sentry_query_params),
                }
            )

        template_name = (
            self.event.occurrence.evidence_data.get("template_name")
            if isinstance(self.event, GroupEvent) and self.event.occurrence
            else None
        )

        if self.group.issue_category == GroupCategory.PERFORMANCE and template_name != "profile":
            # This can't use data from the occurrence at the moment, so we'll keep fetching the event
            # and gathering span evidence.

            # Regression issues don't have span evidence
            if self.group.issue_type not in [
                PerformanceP95EndpointRegressionGroupType,
                ProfileFunctionRegressionType,
            ]:
                context.update(
                    {
                        "transaction_data": [
                            ("Span Evidence", get_transaction_data(self.event), None)
                        ],
                    }
                )
            context.update(
                {
                    "subtitle": get_performance_issue_alert_subtitle(self.event),
                },
            )

        # We don't show the snooze alert if the organization has not enabled the workflow engine UI links
        # This is because in the new UI/system a user can't individually disable a workflow
        if not features.has("organizations:workflow-engine-ui-links", self.organization):
            if len(self.rules) > 0:
                context["snooze_alert"] = True
                context["snooze_alert_url"] = get_snooze_url(
                    self.rules[0],
                    self.organization,
                    self.project,
                    sentry_query_params,
                    self.group.type,
                )
        else:
            context["snooze_alert"] = False
            context["snooze_alert_url"] = None

        if isinstance(self.event, GroupEvent) and self.event.occurrence:
            context["issue_title"] = self.event.occurrence.issue_title
            context["subtitle"] = self.event.occurrence.subtitle
            context["culprit"] = self.event.occurrence.culprit

        if self.group.issue_category not in GROUP_CATEGORIES_CUSTOM_EMAIL:
            generic_issue_data_html = get_generic_data(self.event)
            if generic_issue_data_html:
                context.update(
                    {
                        "generic_issue_data": [("Issue Data", generic_issue_data_html, None)],
                    }
                )

        return context

    def get_notification_title(
        self, provider: ExternalProviders, context: Mapping[str, Any] | None = None
    ) -> str:
        from sentry.integrations.messaging.message_builder import build_rule_url

        title_str = "Alert triggered"

        if self.rules:
            if features.has("organizations:workflow-engine-ui-links", self.organization):
                rule_url = absolute_uri(
                    create_link_to_workflow(
                        self.organization.id, get_key_from_rule_data(self.rules[0], "workflow_id")
                    )
                )
            else:
                rule_url = build_rule_url(self.rules[0], self.group, self.project)
            title_str += (
                f" {self.format_url(text=self.rules[0].label, url=rule_url, provider=provider)}"
            )

            if len(self.rules) > 1:
                title_str += f" (+{len(self.rules) - 1} other)"

        return title_str

    def send(self) -> None:
        from sentry.notifications.notify import notify

        metrics.incr("mail_adapter.notify")
        logger.info(
            "mail.adapter.notify",
            extra={
                "target_type": self.target_type.value,
                "target_identifier": self.target_identifier,
                "group": self.group.id,
                "project_id": self.project.id,
                "organization": self.organization.id,
                "fallthrough_choice": (
                    self.fallthrough_choice.value if self.fallthrough_choice else None
                ),
                "notification_uuid": self.notification_uuid,
            },
        )

        participants_by_provider = self.get_participants()
        if not participants_by_provider:
            logger.info(
                "notifications.notification.rules.alertrulenotification.skip.no_participants",
                extra={
                    "target_type": self.target_type.value,
                    "target_identifier": self.target_identifier,
                    "group": self.group.id,
                    "project_id": self.project.id,
                    "notification_uuid": self.notification_uuid,
                },
            )
            return

        # Only calculate shared context once.
        shared_context = self.get_context()

        for provider, participants in participants_by_provider.items():
            notify(provider, self, participants, shared_context)

    def get_log_params(self, recipient: Actor) -> Mapping[str, Any]:
        return {
            "target_type": self.target_type,
            "target_identifier": self.target_identifier,
            "alert_id": self.rules[0].id if self.rules else None,
            **super().get_log_params(recipient),
        }

    def record_notification_sent(self, recipient: Actor, provider: ExternalProviders) -> None:
        super().record_notification_sent(recipient, provider)
        log_params = self.get_log_params(recipient)
        try:
            analytics.record(
                AlertSentEvent(
                    organization_id=self.organization.id,
                    project_id=self.project.id,
                    provider=provider.name,
                    alert_id=log_params["alert_id"] if log_params["alert_id"] else "",
                    alert_type="issue_alert",
                    external_id=str(recipient.id),
                    notification_uuid=self.notification_uuid,
                )
            )
        except Exception as e:
            sentry_sdk.capture_exception(e)
