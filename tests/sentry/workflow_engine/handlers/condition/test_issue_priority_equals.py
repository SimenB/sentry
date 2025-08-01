from sentry.types.group import PriorityLevel
from sentry.users.services.user.service import user_service
from sentry.workflow_engine.migration_helpers.alert_rule import (
    migrate_alert_rule,
    migrate_metric_data_conditions,
)
from sentry.workflow_engine.models.data_condition import Condition
from sentry.workflow_engine.types import WorkflowEventData
from tests.sentry.workflow_engine.handlers.condition.test_base import ConditionTestCase


class TestIssuePriorityCondition(ConditionTestCase):
    condition = Condition.ISSUE_PRIORITY_EQUALS

    def setUp(self) -> None:
        super().setUp()
        self.event_data = WorkflowEventData(event=self.group_event, group=self.group_event.group)
        self.metric_alert = self.create_alert_rule()
        self.alert_rule_trigger_warning = self.create_alert_rule_trigger(
            alert_rule=self.metric_alert, label="warning"
        )
        self.alert_rule_trigger_critical = self.create_alert_rule_trigger(
            alert_rule=self.metric_alert, label="critical"
        )
        self.rpc_user = user_service.get_user(user_id=self.user.id)
        migrate_alert_rule(self.metric_alert, self.rpc_user)

    def test_simple(self) -> None:
        data_condition_warning_tuple = migrate_metric_data_conditions(
            self.alert_rule_trigger_warning
        )
        data_condition_critical_tuple = migrate_metric_data_conditions(
            self.alert_rule_trigger_critical
        )
        assert data_condition_warning_tuple is not None
        assert data_condition_critical_tuple is not None
        data_condition_warning = data_condition_warning_tuple[1]
        data_condition_critical = data_condition_critical_tuple[1]
        data_condition_critical.type = Condition.ISSUE_PRIORITY_EQUALS
        data_condition_warning.type = Condition.ISSUE_PRIORITY_EQUALS

        self.group.update(priority=PriorityLevel.MEDIUM)
        self.assert_passes(data_condition_warning, self.event_data)
        self.assert_does_not_pass(data_condition_critical, self.event_data)

        self.group.update(priority=PriorityLevel.HIGH)
        self.assert_passes(data_condition_critical, self.event_data)
        self.assert_does_not_pass(data_condition_warning, self.event_data)
