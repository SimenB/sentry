from __future__ import annotations

import enum
from typing import Any, ClassVar

from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.db.models import SET_NULL
from django.utils import timezone

from sentry.backup.scopes import RelocationScope
from sentry.db.models import (
    BoundedPositiveIntegerField,
    FlexibleForeignKey,
    JSONField,
    Model,
    region_silo_model,
    sane_repr,
)
from sentry.db.models.fields.hybrid_cloud_foreign_key import HybridCloudForeignKey
from sentry.db.models.manager.base import BaseManager


# NOTE: There are gaps in the numberation because a
# few tasks were removed as they are no longer used in the quick start sidebar
class OnboardingTask(enum.IntEnum):
    FIRST_PROJECT = 1
    FIRST_EVENT = 2
    INVITE_MEMBER = 3
    SECOND_PLATFORM = 4
    RELEASE_TRACKING = 6
    SOURCEMAPS = 7
    ALERT_RULE = 10
    FIRST_TRANSACTION = 11
    SESSION_REPLAY = 14
    REAL_TIME_NOTIFICATIONS = 15
    LINK_SENTRY_TO_SOURCE_CODE = 16

    @classmethod
    def values(cls) -> list[int]:
        return [member.value for member in cls]


class OnboardingTaskStatus(enum.IntEnum):
    COMPLETE = 1
    # deprecated - no longer used
    # PENDING = 2
    SKIPPED = 3

    @classmethod
    def values(cls) -> list[int]:
        return [member.value for member in cls]


class OrganizationOnboardingTaskManager(BaseManager["OrganizationOnboardingTask"]):
    def record(
        self,
        organization_id: int,
        task: int,
        status: OnboardingTaskStatus = OnboardingTaskStatus.COMPLETE,
        **kwargs,
    ) -> bool:
        """Record the completion of an onboarding task. Caches the completion. Returns whether the task was created or not."""
        if status != OnboardingTaskStatus.COMPLETE:
            raise ValueError(
                f"status={status} unsupported must be {OnboardingTaskStatus.COMPLETE}."
            )

        cache_key = f"organizationonboardingtask:{organization_id}:{task}"

        if cache.get(cache_key) is None:
            defaults = {
                **kwargs,
                "status": status,
            }
            _, created = self.update_or_create(
                organization_id=organization_id,
                task=task,
                defaults=defaults,
            )

            # Store marker to prevent running all the time
            cache.set(cache_key, 1, 3600)
            return created
        return False


class AbstractOnboardingTask(Model):
    """
    An abstract onboarding task that can be subclassed. This abstract model exists so that the Sandbox can create a subclass
    which allows for the creation of tasks that are unique to users instead of organizations.
    """

    __relocation_scope__ = RelocationScope.Excluded

    STATUS_CHOICES = (
        (OnboardingTaskStatus.COMPLETE, "complete"),
        (OnboardingTaskStatus.SKIPPED, "skipped"),
    )

    STATUS_KEY_MAP = dict(STATUS_CHOICES)
    STATUS_LOOKUP_BY_KEY = {v: k for k, v in STATUS_CHOICES}

    organization = FlexibleForeignKey("sentry.Organization")
    user_id = HybridCloudForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete="SET_NULL")
    status = BoundedPositiveIntegerField(choices=[(k, str(v)) for k, v in STATUS_CHOICES])
    completion_seen = models.DateTimeField(null=True)
    date_completed = models.DateTimeField(default=timezone.now)
    project = FlexibleForeignKey(
        "sentry.Project", db_constraint=False, null=True, on_delete=SET_NULL
    )
    # INVITE_MEMBER { invited_member: user.id }
    data: models.Field[dict[str, Any], dict[str, Any]] = JSONField()

    # abstract
    TASK_LOOKUP_BY_KEY: dict[str, int]
    SKIPPABLE_TASKS: frozenset[int]

    class Meta:
        abstract = True


@region_silo_model
class OrganizationOnboardingTask(AbstractOnboardingTask):
    """
    Onboarding tasks walk new Sentry orgs through basic features of Sentry.
    """

    TASK_CHOICES = (
        (OnboardingTask.FIRST_PROJECT, "create_project"),
        (OnboardingTask.FIRST_EVENT, "send_first_event"),
        (OnboardingTask.INVITE_MEMBER, "invite_member"),
        (OnboardingTask.SECOND_PLATFORM, "setup_second_platform"),
        (OnboardingTask.RELEASE_TRACKING, "setup_release_tracking"),
        (OnboardingTask.SOURCEMAPS, "setup_sourcemaps"),
        (OnboardingTask.ALERT_RULE, "setup_alert_rules"),
        (OnboardingTask.FIRST_TRANSACTION, "setup_transactions"),
        (OnboardingTask.SESSION_REPLAY, "setup_session_replay"),
        (OnboardingTask.REAL_TIME_NOTIFICATIONS, "setup_real_time_notifications"),
        (OnboardingTask.LINK_SENTRY_TO_SOURCE_CODE, "link_sentry_to_source_code"),
    )

    # Used in the API to map IDs to string keys. This keeps things
    # a bit more maintainable on the frontend.
    TASK_KEY_MAP = dict(TASK_CHOICES)
    TASK_LOOKUP_BY_KEY = {v: k for k, v in TASK_CHOICES}

    task = BoundedPositiveIntegerField(choices=TASK_CHOICES)

    # Tasks which should be completed for the onboarding to be considered
    # complete.
    REQUIRED_ONBOARDING_TASKS = frozenset(
        [
            OnboardingTask.FIRST_PROJECT,
            OnboardingTask.FIRST_EVENT,
            OnboardingTask.INVITE_MEMBER,
            OnboardingTask.SECOND_PLATFORM,
            OnboardingTask.RELEASE_TRACKING,
            OnboardingTask.ALERT_RULE,
            OnboardingTask.FIRST_TRANSACTION,
            OnboardingTask.SESSION_REPLAY,
            OnboardingTask.REAL_TIME_NOTIFICATIONS,
            OnboardingTask.LINK_SENTRY_TO_SOURCE_CODE,
        ]
    )

    REQUIRED_ONBOARDING_TASKS_WITH_SOURCE_MAPS = frozenset(
        [
            *REQUIRED_ONBOARDING_TASKS,
            OnboardingTask.SOURCEMAPS,
        ]
    )

    SKIPPABLE_TASKS = frozenset(
        [
            OnboardingTask.INVITE_MEMBER,
            OnboardingTask.SECOND_PLATFORM,
            OnboardingTask.RELEASE_TRACKING,
            OnboardingTask.SOURCEMAPS,
            OnboardingTask.ALERT_RULE,
            OnboardingTask.FIRST_TRANSACTION,
            OnboardingTask.SESSION_REPLAY,
            OnboardingTask.REAL_TIME_NOTIFICATIONS,
            OnboardingTask.LINK_SENTRY_TO_SOURCE_CODE,
        ]
    )

    # These are tasks that can be tightened to a project
    TRANSFERABLE_TASKS = frozenset(
        [
            OnboardingTask.FIRST_PROJECT,
            OnboardingTask.FIRST_EVENT,
            OnboardingTask.SECOND_PLATFORM,
            OnboardingTask.RELEASE_TRACKING,
            OnboardingTask.ALERT_RULE,
            OnboardingTask.FIRST_TRANSACTION,
            OnboardingTask.SESSION_REPLAY,
            OnboardingTask.SOURCEMAPS,
        ]
    )

    objects: ClassVar[OrganizationOnboardingTaskManager] = OrganizationOnboardingTaskManager()

    class Meta:
        app_label = "sentry"
        db_table = "sentry_organizationonboardingtask"
        unique_together = (("organization", "task"),)

    __repr__ = sane_repr("organization", "task")
