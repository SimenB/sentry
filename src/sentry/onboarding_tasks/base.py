from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from sentry.models.organization import Organization
from sentry.models.organizationonboardingtask import AbstractOnboardingTask
from sentry.models.project import Project
from sentry.utils.services import Service

T = TypeVar("T", bound=AbstractOnboardingTask)


class OnboardingTaskBackend(Service, Generic[T]):
    __all__ = (
        "get_task_lookup_by_key",
        "get_status_lookup_by_key",
        "get_skippable_tasks",
        "fetch_onboarding_tasks",
        "create_or_update_onboarding_task",
        "complete_onboarding_task",
        "has_completed_onboarding_task",
        "transfer_onboarding_tasks",
        "try_mark_onboarding_complete",
    )
    Model: type[T]

    def get_task_lookup_by_key(self, key):
        return self.Model.TASK_LOOKUP_BY_KEY.get(key)

    def get_status_lookup_by_key(self, key):
        return self.Model.STATUS_LOOKUP_BY_KEY.get(key)

    def get_skippable_tasks(self, organization: Organization):
        return self.Model.SKIPPABLE_TASKS

    def fetch_onboarding_tasks(self, organization, user):
        raise NotImplementedError

    def create_or_update_onboarding_task(self, organization, user, task, values):
        raise NotImplementedError

    def complete_onboarding_task(
        self,
        organization: Organization,
        task: int,
        date_completed: datetime | None = None,
        **task_kwargs,
    ) -> bool:
        raise NotImplementedError

    def has_completed_onboarding_task(self, organization: Organization, task: int) -> bool:
        raise NotImplementedError

    def try_mark_onboarding_complete(self, organization_id: int):
        raise NotImplementedError

    def transfer_onboarding_tasks(
        self,
        from_organization_id: int,
        to_organization_id: int,
        project: Project | None = None,
    ):
        raise NotImplementedError
