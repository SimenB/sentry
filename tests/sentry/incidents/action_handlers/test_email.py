from functools import cached_property
from unittest.mock import MagicMock, patch

import orjson
import pytest
import responses
from django.conf import settings
from django.core import mail
from django.urls import reverse
from django.utils import timezone
from urllib3.response import HTTPResponse

from sentry.analytics.events.alert_sent import AlertSentEvent
from sentry.api.serializers import serialize
from sentry.incidents.action_handlers import (
    EmailActionHandler,
    generate_incident_trigger_email_context,
)
from sentry.incidents.charts import fetch_metric_alert_events_timeseries
from sentry.incidents.endpoints.serializers.alert_rule import (
    AlertRuleSerializer,
    AlertRuleSerializerResponse,
)
from sentry.incidents.endpoints.serializers.incident import (
    DetailedIncidentSerializer,
    DetailedIncidentSerializerResponse,
)
from sentry.incidents.logic import CRITICAL_TRIGGER_LABEL, WARNING_TRIGGER_LABEL
from sentry.incidents.models.alert_rule import (
    AlertRuleDetectionType,
    AlertRuleSeasonality,
    AlertRuleSensitivity,
    AlertRuleThresholdType,
    AlertRuleTriggerAction,
)
from sentry.incidents.models.incident import INCIDENT_STATUS, IncidentStatus, TriggerStatus
from sentry.incidents.typings.metric_detector import (
    AlertContext,
    MetricIssueContext,
    OpenPeriodContext,
)
from sentry.models.groupopenperiod import GroupOpenPeriod
from sentry.notifications.models.notificationsettingoption import NotificationSettingOption
from sentry.seer.anomaly_detection.types import StoreDataResponse
from sentry.sentry_metrics import indexer
from sentry.sentry_metrics.use_case_id_registry import UseCaseID
from sentry.snuba.dataset import Dataset
from sentry.snuba.models import SnubaQuery
from sentry.testutils.cases import TestCase
from sentry.testutils.helpers.analytics import assert_last_analytics_event
from sentry.testutils.helpers.datetime import freeze_time
from sentry.testutils.helpers.features import with_feature
from sentry.testutils.silo import assume_test_silo_mode_of
from sentry.users.models.user_option import UserOption
from sentry.users.models.useremail import UserEmail

from . import FireTest

pytestmark = pytest.mark.sentry_metrics


@freeze_time()
class EmailActionHandlerTest(FireTest):
    @responses.activate
    def run_test(self, incident, method):
        action = self.create_alert_rule_trigger_action(
            target_identifier=str(self.user.id),
            triggered_for_incident=incident,
        )
        handler = EmailActionHandler()
        with self.tasks():
            handler.fire(
                action=action,
                incident=incident,
                project=self.project,
                metric_value=1000,
                new_status=IncidentStatus(incident.status),
            )
        out = mail.outbox[0]
        assert out.to == [self.user.email]
        assert out.subject == "[{}] {} - {}".format(
            INCIDENT_STATUS[IncidentStatus(incident.status)], incident.title, self.project.slug
        )

    def test_fire_metric_alert(self) -> None:
        self.run_fire_test()

    def test_resolve_metric_alert(self) -> None:
        self.run_fire_test("resolve")

    @patch("sentry.analytics.record")
    def test_alert_sent_recorded(self, mock_record: MagicMock) -> None:
        self.run_fire_test()
        assert_last_analytics_event(
            mock_record,
            AlertSentEvent(
                organization_id=self.organization.id,
                project_id=self.project.id,
                provider="email",
                alert_id=str(self.alert_rule.id),
                alert_type="metric_alert",
                external_id=str(self.user.id),
                notification_uuid="",
            ),
        )


class EmailActionHandlerGetTargetsTest(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.handler = EmailActionHandler()

    @cached_property
    def incident(self):
        return self.create_incident()

    def test_user(self) -> None:
        action = self.create_alert_rule_trigger_action(
            target_type=AlertRuleTriggerAction.TargetType.USER,
            target_identifier=str(self.user.id),
        )
        assert self.handler.get_targets(action, self.incident, self.project) == [
            (self.user.id, self.user.email)
        ]

    def test_rule_snoozed_by_user(self) -> None:
        action = self.create_alert_rule_trigger_action(
            target_type=AlertRuleTriggerAction.TargetType.USER,
            target_identifier=str(self.user.id),
        )

        self.snooze_rule(user_id=self.user.id, alert_rule=self.incident.alert_rule)
        assert self.handler.get_targets(action, self.incident, self.project) == []

    def test_user_rule_snoozed(self) -> None:
        action = self.create_alert_rule_trigger_action(
            target_type=AlertRuleTriggerAction.TargetType.USER,
            target_identifier=str(self.user.id),
        )
        self.snooze_rule(alert_rule=self.incident.alert_rule)
        assert self.handler.get_targets(action, self.incident, self.project) == []

    def test_user_alerts_disabled(self) -> None:
        with assume_test_silo_mode_of(NotificationSettingOption):
            NotificationSettingOption.objects.create(
                user_id=self.user.id,
                scope_type="project",
                scope_identifier=self.project.id,
                type="alerts",
                value="never",
            )
        action = self.create_alert_rule_trigger_action(
            target_type=AlertRuleTriggerAction.TargetType.USER,
            target_identifier=str(self.user.id),
        )
        assert self.handler.get_targets(action, self.incident, self.project) == [
            (self.user.id, self.user.email)
        ]

    def test_team(self) -> None:
        new_user = self.create_user()
        self.create_team_membership(team=self.team, user=new_user)
        action = self.create_alert_rule_trigger_action(
            target_type=AlertRuleTriggerAction.TargetType.TEAM,
            target_identifier=str(self.team.id),
        )
        assert set(self.handler.get_targets(action, self.incident, self.project)) == {
            (self.user.id, self.user.email),
            (new_user.id, new_user.email),
        }

    def test_rule_snoozed_by_one_user_in_team(self) -> None:
        new_user = self.create_user()
        self.create_team_membership(team=self.team, user=new_user)
        action = self.create_alert_rule_trigger_action(
            target_type=AlertRuleTriggerAction.TargetType.TEAM,
            target_identifier=str(self.team.id),
        )
        self.snooze_rule(user_id=new_user.id, alert_rule=self.incident.alert_rule)
        assert set(self.handler.get_targets(action, self.incident, self.project)) == {
            (self.user.id, self.user.email),
        }

    def test_team_rule_snoozed(self) -> None:
        new_user = self.create_user()
        self.create_team_membership(team=self.team, user=new_user)
        action = self.create_alert_rule_trigger_action(
            target_type=AlertRuleTriggerAction.TargetType.TEAM,
            target_identifier=str(self.team.id),
        )
        self.snooze_rule(alert_rule=self.incident.alert_rule)
        assert self.handler.get_targets(action, self.incident, self.project) == []

    def test_team_alert_disabled(self) -> None:
        with assume_test_silo_mode_of(NotificationSettingOption):
            NotificationSettingOption.objects.create(
                user_id=self.user.id,
                scope_type="project",
                scope_identifier=self.project.id,
                type="alerts",
                value="never",
            )
            disabled_user = self.create_user()
            NotificationSettingOption.objects.create(
                user_id=disabled_user.id,
                scope_type="user",
                scope_identifier=disabled_user.id,
                type="alerts",
                value="never",
            )

        new_user = self.create_user()
        self.create_team_membership(team=self.team, user=new_user)
        action = self.create_alert_rule_trigger_action(
            target_type=AlertRuleTriggerAction.TargetType.TEAM,
            target_identifier=str(self.team.id),
        )
        assert set(self.handler.get_targets(action, self.incident, self.project)) == {
            (new_user.id, new_user.email),
        }

    def test_user_email_routing(self) -> None:
        new_email = "marcos@sentry.io"
        with assume_test_silo_mode_of(UserOption):
            UserOption.objects.create(
                user=self.user, project_id=self.project.id, key="mail:email", value=new_email
            )

            useremail = UserEmail.objects.get(email=self.user.email)
            useremail.email = new_email
            useremail.save()

        action = self.create_alert_rule_trigger_action(
            target_type=AlertRuleTriggerAction.TargetType.USER,
            target_identifier=str(self.user.id),
        )
        assert self.handler.get_targets(action, self.incident, self.project) == [
            (self.user.id, new_email),
        ]

    def test_team_email_routing(self) -> None:
        new_email = "marcos@sentry.io"

        new_user = self.create_user(new_email)

        with assume_test_silo_mode_of(UserEmail):
            useremail = UserEmail.objects.get(email=self.user.email)
            useremail.email = new_email
            useremail.save()

            UserOption.objects.create(
                user=self.user, project_id=self.project.id, key="mail:email", value=new_email
            )
            UserOption.objects.create(
                user=new_user, project_id=self.project.id, key="mail:email", value=new_email
            )

        self.create_team_membership(team=self.team, user=new_user)
        action = self.create_alert_rule_trigger_action(
            target_type=AlertRuleTriggerAction.TargetType.TEAM,
            target_identifier=str(self.team.id),
        )
        assert self.handler.get_targets(action, self.incident, self.project) == [
            (self.user.id, new_email),
            (new_user.id, new_email),
        ]


@freeze_time()
class EmailActionHandlerGenerateEmailContextTest(TestCase):
    def serialize_incident(self, incident) -> DetailedIncidentSerializerResponse:
        return serialize(incident, None, DetailedIncidentSerializer())

    def serialize_alert_rule(self, alert_rule) -> AlertRuleSerializerResponse:
        return serialize(alert_rule, None, AlertRuleSerializer())

    def _generate_email_context(
        self,
        incident,
        trigger_status,
        trigger_threshold,
        user=None,
        notification_uuid=None,
    ):
        """
        Helper method to generate email context from an incident and trigger status.
        Encapsulates the common pattern of creating contexts and serializing models.
        """
        return generate_incident_trigger_email_context(
            project=self.project,
            organization=incident.organization,
            metric_issue_context=MetricIssueContext.from_legacy_models(
                incident=incident,
                new_status=IncidentStatus(incident.status),
            ),
            alert_rule_serialized_response=self.serialize_alert_rule(incident.alert_rule),
            incident_serialized_response=self.serialize_incident(incident),
            alert_context=AlertContext.from_alert_rule_incident(incident.alert_rule),
            open_period_context=OpenPeriodContext.from_incident(incident),
            trigger_status=trigger_status,
            trigger_threshold=trigger_threshold,
            user=user,
            notification_uuid=notification_uuid,
        )

    def test_simple(self) -> None:
        trigger_status = TriggerStatus.ACTIVE
        alert_rule = self.create_alert_rule()
        incident = self.create_incident(alert_rule=alert_rule)
        action = self.create_alert_rule_trigger_action(triggered_for_incident=incident)
        alert_link = self.organization.absolute_url(
            reverse(
                "sentry-metric-alert",
                kwargs={
                    "organization_slug": incident.organization.slug,
                    "incident_id": incident.identifier,
                },
            ),
            query="referrer=metric_alert_email",
        )
        expected = {
            "link": alert_link,
            "incident_name": incident.title,
            "aggregate": action.alert_rule_trigger.alert_rule.snuba_query.aggregate,
            "query": action.alert_rule_trigger.alert_rule.snuba_query.query,
            "threshold": action.alert_rule_trigger.alert_threshold,
            "status": INCIDENT_STATUS[IncidentStatus(incident.status)],
            "status_key": INCIDENT_STATUS[IncidentStatus(incident.status)].lower(),
            "environment": "All",
            "is_critical": False,
            "is_warning": False,
            "threshold_prefix_string": ">",
            "time_window": "10 minutes",
            "triggered_at": timezone.now(),
            "project_slug": self.project.slug,
            "unsubscribe_link": None,
            "chart_url": None,
            "timezone": settings.SENTRY_DEFAULT_TIME_ZONE,
            "snooze_alert": True,
            "snooze_alert_url": alert_link + "&mute=1",
        }

        assert expected == self._generate_email_context(
            incident=incident,
            trigger_status=trigger_status,
            trigger_threshold=action.alert_rule_trigger.alert_threshold,
        )

    @with_feature("organizations:workflow-engine-trigger-actions")
    def test_simple_with_workflow_engine_dual_write(self) -> None:
        trigger_status = TriggerStatus.ACTIVE
        alert_rule = self.create_alert_rule()
        incident = self.create_incident(alert_rule=alert_rule)
        action = self.create_alert_rule_trigger_action(triggered_for_incident=incident)
        aggregate = action.alert_rule_trigger.alert_rule.snuba_query.aggregate
        alert_link = self.organization.absolute_url(
            reverse(
                "sentry-metric-alert",
                kwargs={
                    "organization_slug": incident.organization.slug,
                    "incident_id": incident.identifier,
                },
            ),
            query="referrer=metric_alert_email",
        )
        expected = {
            "link": alert_link,
            "incident_name": incident.title,
            "aggregate": aggregate,
            "query": action.alert_rule_trigger.alert_rule.snuba_query.query,
            "threshold": action.alert_rule_trigger.alert_threshold,
            "status": INCIDENT_STATUS[IncidentStatus(incident.status)],
            "status_key": INCIDENT_STATUS[IncidentStatus(incident.status)].lower(),
            "environment": "All",
            "is_critical": False,
            "is_warning": False,
            "threshold_prefix_string": ">",
            "time_window": "10 minutes",
            "triggered_at": timezone.now(),
            "project_slug": self.project.slug,
            "unsubscribe_link": None,
            "chart_url": None,
            "timezone": settings.SENTRY_DEFAULT_TIME_ZONE,
            "snooze_alert": True,
            "snooze_alert_url": alert_link + "&mute=1",
        }

        open_period = GroupOpenPeriod.objects.get(group=self.group, project=self.project)
        open_period.update(date_started=timezone.now())
        self.create_incident_group_open_period(incident=incident, group_open_period=open_period)

        metric_issue_context = MetricIssueContext(
            id=self.group.id,
            open_period_identifier=open_period.id,
            title=incident.title,
            snuba_query=incident.alert_rule.snuba_query,
            new_status=IncidentStatus(incident.status),
            subscription=None,
            metric_value=None,
            group=self.group,
        )

        assert expected == generate_incident_trigger_email_context(
            project=self.project,
            organization=incident.organization,
            metric_issue_context=metric_issue_context,
            alert_rule_serialized_response=self.serialize_alert_rule(incident.alert_rule),
            incident_serialized_response=self.serialize_incident(incident),
            alert_context=AlertContext.from_alert_rule_incident(incident.alert_rule),
            open_period_context=OpenPeriodContext.from_incident(incident),
            trigger_status=trigger_status,
            trigger_threshold=action.alert_rule_trigger.alert_threshold,
            user=self.user,
            notification_uuid=None,
        )

    @with_feature("organizations:workflow-engine-ui-links")
    def test_simple_with_workflow_engine_ui_link(self) -> None:
        trigger_status = TriggerStatus.ACTIVE
        alert_rule = self.create_alert_rule()
        incident = self.create_incident(alert_rule=alert_rule)
        action = self.create_alert_rule_trigger_action(triggered_for_incident=incident)
        aggregate = action.alert_rule_trigger.alert_rule.snuba_query.aggregate
        group_link = self.organization.absolute_url(
            reverse(
                "sentry-group",
                kwargs={
                    "organization_slug": incident.organization.slug,
                    "project_id": self.project.id,
                    "group_id": self.group.id,
                },
            ),
            query="referrer=metric_alert_email",
        )
        expected = {
            "link": group_link,
            "incident_name": incident.title,
            "aggregate": aggregate,
            "query": action.alert_rule_trigger.alert_rule.snuba_query.query,
            "threshold": action.alert_rule_trigger.alert_threshold,
            "status": INCIDENT_STATUS[IncidentStatus(incident.status)],
            "status_key": INCIDENT_STATUS[IncidentStatus(incident.status)].lower(),
            "environment": "All",
            "is_critical": False,
            "is_warning": False,
            "threshold_prefix_string": ">",
            "time_window": "10 minutes",
            "triggered_at": timezone.now(),
            "project_slug": self.project.slug,
            "unsubscribe_link": None,
            "chart_url": None,
            "timezone": settings.SENTRY_DEFAULT_TIME_ZONE,
            # We don't have user muting for workflows in the new workflow engine system
            "snooze_alert": False,
            "snooze_alert_url": None,
        }

        open_period = GroupOpenPeriod.objects.get(group=self.group, project=self.project)
        open_period.update(date_started=timezone.now())
        self.create_incident_group_open_period(incident=incident, group_open_period=open_period)

        metric_issue_context = MetricIssueContext(
            id=self.group.id,
            open_period_identifier=open_period.id,
            title=incident.title,
            snuba_query=incident.alert_rule.snuba_query,
            new_status=IncidentStatus(incident.status),
            subscription=None,
            metric_value=None,
            group=self.group,
        )

        assert expected == generate_incident_trigger_email_context(
            project=self.project,
            organization=incident.organization,
            metric_issue_context=metric_issue_context,
            alert_rule_serialized_response=self.serialize_alert_rule(incident.alert_rule),
            incident_serialized_response=self.serialize_incident(incident),
            alert_context=AlertContext.from_alert_rule_incident(incident.alert_rule),
            open_period_context=OpenPeriodContext.from_incident(incident),
            trigger_status=trigger_status,
            trigger_threshold=action.alert_rule_trigger.alert_threshold,
            user=self.user,
            notification_uuid=None,
        )

    @with_feature("organizations:anomaly-detection-alerts")
    @patch(
        "sentry.seer.anomaly_detection.store_data.seer_anomaly_detection_connection_pool.urlopen"
    )
    def test_dynamic_alert(self, mock_seer_request: MagicMock) -> None:

        seer_return_value: StoreDataResponse = {"success": True}
        mock_seer_request.return_value = HTTPResponse(orjson.dumps(seer_return_value), status=200)
        trigger_status = TriggerStatus.ACTIVE
        alert_rule = self.create_alert_rule(
            detection_type=AlertRuleDetectionType.DYNAMIC,
            time_window=30,
            sensitivity=AlertRuleSensitivity.LOW,
            seasonality=AlertRuleSeasonality.AUTO,
        )
        incident = self.create_incident(alert_rule=alert_rule)
        alert_rule_trigger = self.create_alert_rule_trigger(
            alert_rule=alert_rule, alert_threshold=0
        )
        action = self.create_alert_rule_trigger_action(
            alert_rule_trigger=alert_rule_trigger, triggered_for_incident=incident
        )
        aggregate = action.alert_rule_trigger.alert_rule.snuba_query.aggregate
        alert_link = self.organization.absolute_url(
            reverse(
                "sentry-metric-alert",
                kwargs={
                    "organization_slug": incident.organization.slug,
                    "incident_id": incident.identifier,
                },
            ),
            query="?referrer=metric_alert_email&type=anomaly_detection",
        )
        expected = {
            "link": alert_link,
            "incident_name": incident.title,
            "aggregate": aggregate,
            "query": action.alert_rule_trigger.alert_rule.snuba_query.query,
            "threshold": f"({alert_rule.sensitivity} responsiveness)",
            "status": INCIDENT_STATUS[IncidentStatus(incident.status)],
            "status_key": INCIDENT_STATUS[IncidentStatus(incident.status)].lower(),
            "environment": "All",
            "is_critical": False,
            "is_warning": False,
            "threshold_prefix_string": "Dynamic",
            "time_window": "30 minutes",
            "triggered_at": timezone.now(),
            "project_slug": self.project.slug,
            "unsubscribe_link": None,
            "chart_url": None,
            "timezone": settings.SENTRY_DEFAULT_TIME_ZONE,
            "snooze_alert": True,
            "snooze_alert_url": alert_link + "&mute=1",
        }
        assert expected == self._generate_email_context(
            incident=incident,
            trigger_status=trigger_status,
            trigger_threshold=action.alert_rule_trigger.alert_threshold,
            user=self.user,
        )

    @with_feature("system:multi-region")
    def test_links_customer_domains(self) -> None:
        trigger_status = TriggerStatus.ACTIVE
        incident = self.create_incident()
        action = self.create_alert_rule_trigger_action(triggered_for_incident=incident)
        result = self._generate_email_context(
            incident=incident,
            trigger_status=trigger_status,
            trigger_threshold=action.alert_rule_trigger.alert_threshold,
            user=self.user,
        )
        path = reverse(
            "sentry-metric-alert",
            kwargs={
                "organization_slug": self.organization.slug,
                "incident_id": incident.identifier,
            },
        )
        assert self.organization.absolute_url(path) in result["link"]

    def test_resolve(self) -> None:
        status = TriggerStatus.RESOLVED
        alert_rule = self.create_alert_rule()
        incident = self.create_incident(alert_rule=alert_rule)
        alert_rule_trigger = self.create_alert_rule_trigger(alert_rule=alert_rule)
        action = self.create_alert_rule_trigger_action(
            alert_rule_trigger=alert_rule_trigger, triggered_for_incident=incident
        )
        generated_email_context = self._generate_email_context(
            incident=incident,
            trigger_status=status,
            trigger_threshold=action.alert_rule_trigger.alert_threshold,
            user=self.user,
        )
        assert generated_email_context["threshold"] == 100

    def test_resolve_critical_trigger_with_warning(self) -> None:
        status = TriggerStatus.RESOLVED
        rule = self.create_alert_rule()
        incident = self.create_incident(alert_rule=rule, status=IncidentStatus.WARNING.value)
        crit_trigger = self.create_alert_rule_trigger(rule, CRITICAL_TRIGGER_LABEL, 100)
        self.create_alert_rule_trigger_action(crit_trigger, triggered_for_incident=incident)
        self.create_alert_rule_trigger(rule, WARNING_TRIGGER_LABEL, 50)
        generated_email_context = self._generate_email_context(
            incident=incident,
            trigger_status=status,
            trigger_threshold=crit_trigger.alert_threshold,
            user=self.user,
        )
        assert generated_email_context["threshold"] == 100
        assert generated_email_context["threshold_prefix_string"] == "<"
        assert not generated_email_context["is_critical"]
        assert generated_email_context["is_warning"]
        assert generated_email_context["status"] == "Warning"
        assert generated_email_context["status_key"] == "warning"

    def test_context_for_crash_rate_alert(self) -> None:
        """
        Test that ensures the metric name for Crash rate alerts excludes the alias
        """
        status = TriggerStatus.ACTIVE
        alert_rule = self.create_alert_rule(
            aggregate="percentage(sessions_crashed, sessions) AS _crash_rate_alert_aggregate"
        )
        incident = self.create_incident(alert_rule=alert_rule)
        alert_rule_trigger = self.create_alert_rule_trigger(alert_rule)
        action = self.create_alert_rule_trigger_action(
            alert_rule_trigger=alert_rule_trigger, triggered_for_incident=incident
        )
        assert (
            self._generate_email_context(
                incident=incident,
                trigger_status=status,
                trigger_threshold=action.alert_rule_trigger.alert_threshold,
                user=self.user,
            )["aggregate"]
            == "percentage(sessions_crashed, sessions)"
        )

    def test_context_for_resolved_crash_rate_alert(self) -> None:
        """
        Test that ensures the resolved notification contains the correct threshold string
        """
        status = TriggerStatus.RESOLVED
        alert_rule = self.create_alert_rule(
            aggregate="percentage(sessions_crashed, sessions) AS _crash_rate_alert_aggregate",
            threshold_type=AlertRuleThresholdType.BELOW,
            query="",
        )
        incident = self.create_incident(alert_rule=alert_rule)
        alert_rule_trigger = self.create_alert_rule_trigger(alert_rule)
        action = self.create_alert_rule_trigger_action(
            alert_rule_trigger=alert_rule_trigger, triggered_for_incident=incident
        )
        generated_email_context = self._generate_email_context(
            incident=incident,
            trigger_status=status,
            trigger_threshold=action.alert_rule_trigger.alert_threshold,
            user=self.user,
        )
        assert generated_email_context["aggregate"] == "percentage(sessions_crashed, sessions)"
        assert generated_email_context["threshold"] == 100
        assert generated_email_context["threshold_prefix_string"] == ">"

    def test_environment(self) -> None:
        status = TriggerStatus.ACTIVE
        environments = [
            self.create_environment(project=self.project, name="prod"),
            self.create_environment(project=self.project, name="dev"),
        ]
        alert_rule = self.create_alert_rule(environment=environments[0])
        alert_rule_trigger = self.create_alert_rule_trigger(alert_rule=alert_rule)
        incident = self.create_incident(alert_rule=alert_rule)
        action = self.create_alert_rule_trigger_action(
            alert_rule_trigger=alert_rule_trigger, triggered_for_incident=incident
        )
        assert "prod" == self._generate_email_context(
            incident=incident,
            trigger_status=status,
            trigger_threshold=action.alert_rule_trigger.alert_threshold,
            user=self.user,
        ).get("environment")

    @patch(
        "sentry.incidents.charts.fetch_metric_alert_events_timeseries",
        side_effect=fetch_metric_alert_events_timeseries,
    )
    @patch("sentry.charts.backend.generate_chart", return_value="chart-url")
    def test_metric_chart(
        self, mock_generate_chart: MagicMock, mock_fetch_metric_alert_events_timeseries: MagicMock
    ) -> None:
        trigger_status = TriggerStatus.ACTIVE
        alert_rule = self.create_alert_rule()
        incident = self.create_incident(alert_rule=alert_rule)
        alert_rule_trigger = self.create_alert_rule_trigger(alert_rule=alert_rule)
        action = self.create_alert_rule_trigger_action(
            alert_rule_trigger=alert_rule_trigger, triggered_for_incident=incident
        )

        with self.feature(
            [
                "organizations:incidents",
                "organizations:discover",
                "organizations:discover-basic",
                "organizations:metric-alert-chartcuterie",
            ]
        ):
            result = self._generate_email_context(
                incident=incident,
                trigger_status=trigger_status,
                trigger_threshold=action.alert_rule_trigger.alert_threshold,
                user=self.user,
            )
        assert result["chart_url"] == "chart-url"
        chart_data = mock_generate_chart.call_args[0][1]
        assert chart_data["rule"]["id"] == str(incident.alert_rule.id)
        assert chart_data["selectedIncident"]["identifier"] == str(incident.identifier)
        assert mock_fetch_metric_alert_events_timeseries.call_args[0][2]["dataset"] == "errors"
        series_data = chart_data["timeseriesData"][0]["data"]
        assert len(series_data) > 0
        assert mock_generate_chart.call_args[1]["size"] == {"width": 600, "height": 200}

    @patch(
        "sentry.incidents.charts.fetch_metric_alert_events_timeseries",
        side_effect=fetch_metric_alert_events_timeseries,
    )
    @patch("sentry.charts.backend.generate_chart", return_value="chart-url")
    def test_metric_chart_mep(
        self, mock_generate_chart: MagicMock, mock_fetch_metric_alert_events_timeseries: MagicMock
    ) -> None:
        indexer.record(
            use_case_id=UseCaseID.TRANSACTIONS, org_id=self.organization.id, string="level"
        )
        trigger_status = TriggerStatus.ACTIVE
        alert_rule = self.create_alert_rule(
            query_type=SnubaQuery.Type.PERFORMANCE, dataset=Dataset.PerformanceMetrics
        )
        incident = self.create_incident(alert_rule=alert_rule)
        alert_rule_trigger = self.create_alert_rule_trigger(alert_rule=alert_rule)
        action = self.create_alert_rule_trigger_action(
            alert_rule_trigger=alert_rule_trigger, triggered_for_incident=incident
        )

        with self.feature(
            [
                "organizations:incidents",
                "organizations:discover",
                "organizations:discover-basic",
                "organizations:metric-alert-chartcuterie",
            ]
        ):
            result = self._generate_email_context(
                incident=incident,
                trigger_status=trigger_status,
                trigger_threshold=action.alert_rule_trigger.alert_threshold,
                user=self.user,
            )
        assert result["chart_url"] == "chart-url"
        chart_data = mock_generate_chart.call_args[0][1]
        assert chart_data["rule"]["id"] == str(incident.alert_rule.id)
        assert chart_data["selectedIncident"]["identifier"] == str(incident.identifier)
        assert mock_fetch_metric_alert_events_timeseries.call_args[0][2]["dataset"] == "metrics"
        series_data = chart_data["timeseriesData"][0]["data"]
        assert len(series_data) > 0
        assert mock_generate_chart.call_args[1]["size"] == {"width": 600, "height": 200}

    def test_timezones(self) -> None:
        trigger_status = TriggerStatus.ACTIVE
        alert_rule = self.create_alert_rule(
            query_type=SnubaQuery.Type.PERFORMANCE, dataset=Dataset.PerformanceMetrics
        )
        incident = self.create_incident(alert_rule=alert_rule)
        alert_rule_trigger = self.create_alert_rule_trigger(alert_rule=alert_rule)
        action = self.create_alert_rule_trigger_action(
            alert_rule_trigger=alert_rule_trigger, triggered_for_incident=incident
        )

        est = "America/New_York"
        pst = "US/Pacific"
        with assume_test_silo_mode_of(UserOption):
            UserOption.objects.set_value(user=self.user, key="timezone", value=est)
        result = self._generate_email_context(
            incident=incident,
            trigger_status=trigger_status,
            trigger_threshold=action.alert_rule_trigger.alert_threshold,
            user=self.user,
        )
        assert result["timezone"] == est

        with assume_test_silo_mode_of(UserOption):
            UserOption.objects.set_value(user=self.user, key="timezone", value=pst)
        result = self._generate_email_context(
            incident=incident,
            trigger_status=trigger_status,
            trigger_threshold=action.alert_rule_trigger.alert_threshold,
            user=self.user,
        )
        assert result["timezone"] == pst
