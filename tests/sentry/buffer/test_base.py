from datetime import timedelta
from unittest import mock

from django.utils import timezone
from pytest import raises

from sentry.buffer.base import Buffer, BufferField
from sentry.models.group import Group
from sentry.models.organization import Organization
from sentry.models.project import Project
from sentry.models.release import Release
from sentry.models.releases.release_project import ReleaseProject
from sentry.models.team import Team
from sentry.receivers import create_default_projects
from sentry.testutils.cases import TestCase


class BufferTest(TestCase):
    def setUp(self) -> None:
        create_default_projects()
        self.buf = Buffer()

    @mock.patch("sentry.buffer.base.process_incr")
    def test_incr_delays_task(self, process_incr: mock.MagicMock) -> None:
        model = Group
        columns = {"times_seen": 1}
        filters: dict[str, BufferField] = {"id": 1}
        self.buf.incr(model, columns, filters)
        kwargs = dict(
            model_name="sentry.group",
            columns=columns,
            filters=filters,
            extra=None,
            signal_only=None,
        )
        process_incr.apply_async.assert_called_once_with(kwargs=kwargs, headers=mock.ANY)

    def test_process_saves_data(self) -> None:
        group = Group.objects.create(project=Project(id=1))
        columns = {"times_seen": 1}
        filters = {"id": group.id, "project_id": 1}
        self.buf.process(Group, columns, filters)
        assert Group.objects.get(id=group.id).times_seen == group.times_seen + 1

    def test_process_saves_data_without_existing_row(self) -> None:
        columns = {"new_groups": 1}
        filters = {"project_id": self.project.id, "release_id": self.release.id}
        self.buf.process(ReleaseProject, columns, filters)
        assert ReleaseProject.objects.filter(new_groups=1, **filters).exists()

    def test_process_saves_extra(self) -> None:
        group = Group.objects.create(project=Project(id=1))
        columns = {"times_seen": 1}
        filters = {"id": group.id, "project_id": 1}
        the_date = timezone.now() + timedelta(days=5)
        self.buf.process(Group, columns, filters, {"last_seen": the_date})
        reload = Group.objects.get(id=group.id)
        assert reload.times_seen == group.times_seen + 1
        assert reload.last_seen == the_date

    def test_increments_when_null(self) -> None:
        org = Organization.objects.create(slug="test-org")
        team = Team.objects.create(organization=org, slug="test-team")
        project = Project.objects.create(organization=org, slug="test-project")
        project.add_team(team)
        release = Release.objects.create(organization=org, version="abcdefg")
        release_project = ReleaseProject.objects.create(project=project, release=release)
        assert release_project.new_groups == 0

        columns = {"new_groups": 1}
        filters = {"id": release_project.id}
        self.buf.process(ReleaseProject, columns, filters)
        release_project_ = ReleaseProject.objects.get(id=release_project.id)
        assert release_project_.new_groups == 1

    @mock.patch("sentry.models.Group.objects.create_or_update")
    def test_signal_only(self, create_or_update: mock.MagicMock) -> None:
        group = Group.objects.create(project=Project(id=1))
        columns = {"times_seen": 1}
        filters = {"id": group.id, "project_id": 1}
        the_date = timezone.now() + timedelta(days=5)
        prev_times_seen = group.times_seen
        self.buf.process(Group, columns, filters, {"last_seen": the_date}, signal_only=True)
        group.refresh_from_db()
        assert group.times_seen == prev_times_seen

    def test_push_to_hash_bulk(self) -> None:
        raises(NotImplementedError, self.buf.push_to_hash_bulk, Group, {"id": 1}, {"foo": "bar"})

    def test_get_hash_length(self) -> None:
        raises(NotImplementedError, self.buf.get_hash_length, Group, {"id": 1})
