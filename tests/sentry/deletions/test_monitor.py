from sentry.deletions.tasks.scheduled import run_scheduled_deletions
from sentry.models.environment import Environment
from sentry.models.project import Project
from sentry.monitors.models import (
    CheckInStatus,
    Monitor,
    MonitorCheckIn,
    MonitorEnvironment,
    ScheduleType,
)
from sentry.testutils.cases import APITestCase, TransactionTestCase
from sentry.testutils.hybrid_cloud import HybridCloudTestMixin


class DeleteMonitorTest(APITestCase, TransactionTestCase, HybridCloudTestMixin):
    def test_simple(self) -> None:
        project = self.create_project(name="test")
        env = Environment.objects.create(organization_id=project.organization_id, name="foo")

        monitor = Monitor.objects.create(
            organization_id=project.organization.id,
            project_id=project.id,
            config={"schedule": "* * * * *", "schedule_type": ScheduleType.CRONTAB},
        )
        monitor_env = MonitorEnvironment.objects.create(
            monitor=monitor,
            environment_id=env.id,
        )
        checkin = MonitorCheckIn.objects.create(
            monitor=monitor,
            monitor_environment=monitor_env,
            project_id=project.id,
            date_added=monitor.date_added,
            status=CheckInStatus.OK,
        )

        self.ScheduledDeletion.schedule(instance=monitor, days=0)

        with self.tasks():
            run_scheduled_deletions()

        assert not Monitor.objects.filter(id=monitor.id).exists()
        assert not MonitorEnvironment.objects.filter(id=monitor_env.id).exists()
        assert not MonitorCheckIn.objects.filter(id=checkin.id).exists()

        # Shared objects should continue to exist.
        assert Environment.objects.filter(id=env.id).exists()
        assert Project.objects.filter(id=project.id).exists()
