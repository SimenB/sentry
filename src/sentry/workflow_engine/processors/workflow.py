from collections.abc import Collection, Mapping
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from enum import StrEnum
from typing import DefaultDict

import sentry_sdk
from django.db import router, transaction
from django.db.models import Q
from django.utils import timezone

from sentry import buffer, features
from sentry.eventstore.models import GroupEvent
from sentry.models.activity import Activity
from sentry.models.environment import Environment
from sentry.utils import json
from sentry.workflow_engine.models import (
    Action,
    DataCondition,
    DataConditionGroup,
    Detector,
    Workflow,
)
from sentry.workflow_engine.models.workflow_data_condition_group import WorkflowDataConditionGroup
from sentry.workflow_engine.processors.action import filter_recently_fired_workflow_actions
from sentry.workflow_engine.processors.contexts.workflow_event_context import (
    WorkflowEventContext,
    WorkflowEventContextData,
)
from sentry.workflow_engine.processors.data_condition_group import process_data_condition_group
from sentry.workflow_engine.processors.detector import get_detector_by_event
from sentry.workflow_engine.processors.workflow_fire_history import create_workflow_fire_histories
from sentry.workflow_engine.tasks.actions import build_trigger_action_task_params, trigger_action
from sentry.workflow_engine.types import WorkflowEventData
from sentry.workflow_engine.utils import log_context
from sentry.workflow_engine.utils.metrics import metrics_incr

logger = log_context.get_logger(__name__)

WORKFLOW_ENGINE_BUFFER_LIST_KEY = "workflow_engine_delayed_processing_buffer"
DetectorId = int | None


class WorkflowDataConditionGroupType(StrEnum):
    ACTION_FILTER = "action_filter"
    WORKFLOW_TRIGGER = "workflow_trigger"


def delete_workflow(workflow: Workflow) -> bool:
    with transaction.atomic(router.db_for_write(Workflow)):
        action_filters = DataConditionGroup.objects.filter(
            workflowdataconditiongroup__workflow=workflow
        )

        actions = Action.objects.filter(
            dataconditiongroupaction__condition_group__in=action_filters
        )

        # Delete the actions associated with a workflow, this is not a cascade delete
        # because we want to create a UI to maintain notification actions separately
        if actions:
            actions.delete()

        if action_filters:
            action_filters.delete()

        if workflow.when_condition_group:
            workflow.when_condition_group.delete()

        workflow.delete()

    return True


@dataclass(frozen=True)
class DelayedWorkflowItem:
    workflow: Workflow
    delayed_conditions: list[DataCondition]
    event: GroupEvent
    source: WorkflowDataConditionGroupType

    # Used to pick the end of the time window in snuba querying.
    # Should be close to when fast conditions were evaluated to try to be consistent.
    timestamp: datetime

    def buffer_key(self) -> str:
        condition_group_set = {
            condition.condition_group_id for condition in self.delayed_conditions
        }
        condition_groups = ",".join(
            str(condition_group_id) for condition_group_id in sorted(condition_group_set)
        )
        return f"{self.workflow.id}:{self.event.group.id}:{condition_groups}:{self.source}"

    def buffer_value(self) -> str:
        return json.dumps(
            {
                "event_id": self.event.event_id,
                "occurrence_id": self.event.occurrence_id,
                "timestamp": self.timestamp,
            }
        )


def enqueue_workflows(
    items_by_project_id: Mapping[int, Collection[DelayedWorkflowItem]],
) -> None:
    if not items_by_project_id:
        return
    for project_id, queue_items in items_by_project_id.items():
        buffer.backend.push_to_hash_bulk(
            model=Workflow,
            filters={"project_id": project_id},
            data={queue_item.buffer_key(): queue_item.buffer_value() for queue_item in queue_items},
        )

    buffer.backend.push_to_sorted_set(
        key=WORKFLOW_ENGINE_BUFFER_LIST_KEY, value=list(items_by_project_id.keys())
    )


@sentry_sdk.trace
def evaluate_workflow_triggers(
    workflows: set[Workflow], event_data: WorkflowEventData
) -> set[Workflow]:
    triggered_workflows: set[Workflow] = set()
    queue_items_by_project_id = DefaultDict[int, list[DelayedWorkflowItem]](list)
    current_time = timezone.now()

    for workflow in workflows:
        evaluation, remaining_conditions = workflow.evaluate_trigger_conditions(event_data)

        if remaining_conditions:
            if isinstance(event_data.event, GroupEvent):
                queue_items_by_project_id[event_data.event.group.project_id].append(
                    DelayedWorkflowItem(
                        workflow,
                        remaining_conditions,
                        event_data.event,
                        WorkflowDataConditionGroupType.WORKFLOW_TRIGGER,
                        timestamp=current_time,
                    )
                )
            else:
                """
                Tracking when we try to enqueue a slow condition for an activity.
                Currently, we are assuming those cases are evaluating as True since
                an activity update is meant to respond to a previous event.
                """
                metrics_incr("process_workflows.enqueue_workflow.activity")
                logger.info(
                    "workflow_engine.process_workflows.enqueue_workflow.activity",
                    extra={
                        "event_id": event_data.event.id,
                        "workflow_id": workflow.id,
                    },
                )
        else:
            if evaluation:
                triggered_workflows.add(workflow)

    enqueue_workflows(queue_items_by_project_id)

    metrics_incr(
        "process_workflows.triggered_workflows",
        len(triggered_workflows),
    )

    # TODO - Remove `environment` access once it's in the shared logger.
    environment = WorkflowEventContext.get().environment
    if environment is None:
        try:
            environment = get_environment_by_event(event_data)
        except Environment.DoesNotExist:
            return set()

    event_id = (
        event_data.event.event_id
        if isinstance(event_data.event, GroupEvent)
        else event_data.event.id
    )
    logger.info(
        "workflow_engine.process_workflows.triggered_workflows",
        extra={
            "group_id": event_data.group.id,
            "event_id": event_id,
            "event_data": asdict(event_data),
            "event_environment_id": environment.id if environment else None,
            "triggered_workflows": [workflow.id for workflow in triggered_workflows],
        },
    )

    return triggered_workflows


def evaluate_action_filters(
    event_data: WorkflowEventData,
    dcg_to_workflow: dict[DataConditionGroup, Workflow],
) -> set[DataConditionGroup]:
    """
    Evaluate the action filters for the given mapping of DataConditionGroup to Workflow. (dcg_to_workflow_id)
    Returns a set of DataConditionGroups that were evaluated to True.

    Use this function if you are repeatedly evaluating action filters in a loop --
    query for all the DataConditionGroups in a single query before using this function to avoid N+1s queries.
    """
    filtered_action_groups: set[DataConditionGroup] = set()
    queue_items_by_project_id = DefaultDict[int, list[DelayedWorkflowItem]](list)
    current_time = timezone.now()

    for action_condition, workflow in dcg_to_workflow.items():
        env = (
            Environment.objects.get_from_cache(id=workflow.environment_id)
            if workflow.environment_id
            else None
        )
        workflow_event_data = replace(event_data, workflow_env=env)
        group_evaluation, slow_conditions = process_data_condition_group(
            action_condition, workflow_event_data
        )

        if slow_conditions:
            # If there are remaining conditions for the action filter to evaluate,
            # then return the list of conditions to enqueue.

            if isinstance(event_data.event, GroupEvent):
                # `delayed_workflows` only supports group events
                queue_items_by_project_id[event_data.event.group.project_id].append(
                    DelayedWorkflowItem(
                        workflow,
                        slow_conditions,
                        event_data.event,
                        WorkflowDataConditionGroupType.ACTION_FILTER,
                        timestamp=current_time,
                    )
                )
            else:
                # We should not include activity updates in delayed conditions,
                # this is because the actions should always be triggered if this condition is met.
                # The original snuba queries would have to be over threshold to create this event
                metrics_incr("process_workflows.enqueue_workflow.activity")
                logger.info(
                    "workflow_engine.process_workflows.enqueue_workflow.activity",
                    extra={
                        "event_id": event_data.event.id,
                        "action_condition_id": action_condition.id,
                        "workflow_id": workflow.id,
                    },
                )
        else:
            if group_evaluation.logic_result:
                filtered_action_groups.add(action_condition)

    enqueue_workflows(queue_items_by_project_id)

    event_id = (
        event_data.event.event_id
        if isinstance(event_data.event, GroupEvent)
        else event_data.event.id
    )

    logger.debug(
        "workflow_engine.evaluate_workflows_action_filters",
        extra={
            "group_id": event_data.group.id,
            "event_id": event_id,
            "workflow_ids": [workflow.id for workflow in dcg_to_workflow.values()],
            "action_conditions": [
                action_condition.id for action_condition in dcg_to_workflow.keys()
            ],
            "filtered_action_groups": [action_group.id for action_group in filtered_action_groups],
        },
    )

    return filtered_action_groups


@sentry_sdk.trace
def evaluate_workflows_action_filters(
    workflows: set[Workflow],
    event_data: WorkflowEventData,
) -> set[DataConditionGroup]:
    """
    Evaluate the action filters for the given workflows.
    Returns a set of DataConditionGroups that were evaluated to True.

    Use this function if you only have a set of workflows to evaluate and will not repeatedly evaluate action filters in a loop.
    """
    action_conditions_to_workflow = {
        wdcg.condition_group: wdcg.workflow
        for wdcg in WorkflowDataConditionGroup.objects.select_related(
            "workflow", "condition_group"
        ).filter(workflow__in=workflows)
    }

    return evaluate_action_filters(event_data, action_conditions_to_workflow)


def get_environment_by_event(event_data: WorkflowEventData) -> Environment | None:
    if isinstance(event_data.event, GroupEvent):
        try:
            environment = event_data.event.get_environment()
        except Environment.DoesNotExist:
            metrics_incr("process_workflows.error")
            logger.exception(
                "Missing environment for event", extra={"event_id": event_data.event.event_id}
            )
            raise Environment.DoesNotExist("Environment does not exist for the event")

        return environment
    elif isinstance(event_data.event, Activity):
        return None

    raise TypeError(f"Cannot access the environment from, {type(event_data.event)}.")


def _get_associated_workflows(
    detector: Detector, environment: Environment | None, event_data: WorkflowEventData
) -> set[Workflow]:
    """
    This is a wrapper method to get the workflows associated with a detector and environment.
    Used in process_workflows to wrap the query + logging into a single method
    """
    environment_filter = (
        (Q(environment_id=None) | Q(environment_id=environment.id))
        if environment
        else Q(environment_id=None)
    )
    workflows = set(
        Workflow.objects.filter(
            environment_filter,
            detectorworkflow__detector_id=detector.id,
            enabled=True,
        )
        .select_related("environment")
        .distinct()
    )

    if workflows:
        metrics_incr(
            "process_workflows",
            len(workflows),
        )

        event_id = (
            event_data.event.event_id
            if isinstance(event_data.event, GroupEvent)
            else event_data.event.id
        )
        logger.info(
            "workflow_engine.process_workflows",
            extra={
                "payload": event_data,
                "group_id": event_data.group.id,
                "event_id": event_id,
                "event_data": asdict(event_data),
                "event_environment_id": environment.id if environment else None,
                "workflows": [workflow.id for workflow in workflows],
                "detector_type": detector.type,
            },
        )

    return workflows


@log_context.root()
def process_workflows(
    event_data: WorkflowEventData, detector: Detector | None = None
) -> set[Workflow]:
    """
    This method will get the detector based on the event, and then gather the associated workflows.
    Next, it will evaluate the "when" (or trigger) conditions for each workflow, if the conditions are met,
    the workflow will be added to a unique list of triggered workflows.

    Finally, each of the triggered workflows will have their actions evaluated and executed.
    """
    from sentry.notifications.notification_action.utils import should_fire_workflow_actions

    try:
        if detector is None and isinstance(event_data.event, GroupEvent):
            detector = get_detector_by_event(event_data)

        if detector is None:
            raise ValueError("Unable to determine the detector for the event")

        log_context.add_extras(detector_id=detector.id)
        organization = detector.project.organization

        # set the detector / org information asap, this is used in `get_environment_by_event` as well.
        WorkflowEventContext.set(
            WorkflowEventContextData(
                detector=detector,
                organization=organization,
            )
        )
    except Detector.DoesNotExist:
        return set()

    try:
        environment = get_environment_by_event(event_data)

        # Set the full context now that we've gotten everything.
        WorkflowEventContext.set(
            WorkflowEventContextData(
                detector=detector,
                environment=environment,
                organization=organization,
            )
        )
    except Environment.DoesNotExist:
        return set()

    if features.has(
        "organizations:workflow-engine-metric-alert-dual-processing-logs", organization
    ):
        log_context.set_verbose(True)

    workflows = _get_associated_workflows(detector, environment, event_data)
    if not workflows:
        # If there aren't any workflows, there's nothing to evaluate
        return set()

    triggered_workflows = evaluate_workflow_triggers(workflows, event_data)
    if not triggered_workflows:
        # if there aren't any triggered workflows, there's no action filters to evaluate
        return set()

    actions_to_trigger = evaluate_workflows_action_filters(triggered_workflows, event_data)
    actions = filter_recently_fired_workflow_actions(actions_to_trigger, event_data)

    if not actions:
        # If there aren't any actions on the associated workflows, there's nothing to trigger
        return triggered_workflows

    should_trigger_actions = should_fire_workflow_actions(organization, event_data.group.type)

    create_workflow_fire_histories(detector, actions, event_data, should_trigger_actions)

    for action in actions:
        task_params = build_trigger_action_task_params(action, detector, event_data)
        trigger_action.delay(**task_params)

    return triggered_workflows
