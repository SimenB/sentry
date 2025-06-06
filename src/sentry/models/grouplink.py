from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from django.db import models
from django.db.models import QuerySet
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from sentry.backup.scopes import RelocationScope
from sentry.db.models import (
    BoundedBigIntegerField,
    BoundedPositiveIntegerField,
    FlexibleForeignKey,
    JSONField,
    Model,
    region_silo_model,
    sane_repr,
)
from sentry.db.models.manager.base import BaseManager

if TYPE_CHECKING:
    from sentry.models.group import Group


class GroupLinkManager(BaseManager["GroupLink"]):
    def get_group_issues(self, group: Group, external_issue_id: str | None = None) -> QuerySet:
        kwargs = dict(
            group=group,
            project_id=group.project_id,
            linked_type=GroupLink.LinkedType.issue,
            relationship=GroupLink.Relationship.references,
        )

        if external_issue_id is not None:
            kwargs["linked_id"] = external_issue_id
        return self.filter(**kwargs)


@region_silo_model
class GroupLink(Model):
    """
    Link a group with an external resource like a commit, issue, or pull request
    """

    __relocation_scope__ = RelocationScope.Excluded

    class Relationship:
        unknown = 0
        resolves = 1
        references = 2

    class LinkedType:
        unknown = 0
        commit = 1
        pull_request = 2
        issue = 3

    group = FlexibleForeignKey("sentry.Group", db_constraint=False, db_index=False)
    project = FlexibleForeignKey("sentry.Project", db_constraint=False, db_index=True)
    linked_type = BoundedPositiveIntegerField(
        default=LinkedType.commit,
        choices=(
            (LinkedType.commit, _("Commit")),
            (LinkedType.pull_request, _("Pull Request")),
            (LinkedType.issue, _("Tracker Issue")),
        ),
    )
    linked_id = BoundedBigIntegerField()
    relationship = BoundedPositiveIntegerField(
        default=Relationship.references,
        choices=((Relationship.resolves, _("Resolves")), (Relationship.references, _("Linked"))),
    )
    data: models.Field[dict[str, Any], dict[str, Any]] = JSONField()
    datetime = models.DateTimeField(default=timezone.now, db_index=True)

    objects: ClassVar[GroupLinkManager] = GroupLinkManager()

    class Meta:
        app_label = "sentry"
        db_table = "sentry_grouplink"
        unique_together = (("group", "linked_type", "linked_id"),)
        indexes = [models.Index(fields=["project", "linked_id", "linked_type", "group"])]

    __repr__ = sane_repr("group_id", "linked_type", "linked_id", "relationship", "datetime")
