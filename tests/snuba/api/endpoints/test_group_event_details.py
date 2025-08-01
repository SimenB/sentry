from sentry.models.group import Group
from sentry.testutils.cases import APITestCase, PerformanceIssueTestCase, SnubaTestCase
from sentry.testutils.helpers.datetime import before_now


class GroupEventDetailsTest(APITestCase, SnubaTestCase, PerformanceIssueTestCase):
    def setUp(self):
        super().setUp()
        self.login_as(user=self.user)

        project = self.create_project()
        min_ago = before_now(minutes=1).isoformat()
        two_min_ago = before_now(minutes=2).isoformat()

        self.event1 = self.store_event(
            data={
                "event_id": "a" * 32,
                "environment": "staging",
                "fingerprint": ["group_1"],
                "timestamp": two_min_ago,
            },
            project_id=project.id,
        )

        self.event2 = self.store_event(
            data={
                "event_id": "b" * 32,
                "environment": "production",
                "fingerprint": ["group_1"],
                "timestamp": min_ago,
            },
            project_id=project.id,
        )

        self.group = Group.objects.first()

    def test_snuba_no_environment_latest(self) -> None:
        url = f"/api/0/issues/{self.group.id}/events/latest/"
        response = self.client.get(url, format="json")

        assert response.status_code == 200
        assert response.data["id"] == str(self.event2.event_id)

    def test_snuba_no_environment_oldest(self) -> None:
        url = f"/api/0/issues/{self.group.id}/events/oldest/"
        response = self.client.get(url, format="json")

        assert response.status_code == 200
        assert response.data["id"] == str(self.event1.event_id)

    def test_snuba_no_environment_event_id(self) -> None:
        url = f"/api/0/issues/{self.group.id}/events/{self.event1.event_id}/"
        response = self.client.get(url, format="json")

        assert response.status_code == 200
        assert response.data["id"] == str(self.event1.event_id)

    def test_snuba_environment_latest(self) -> None:
        url = f"/api/0/issues/{self.group.id}/events/latest/"
        response = self.client.get(url, format="json", data={"environment": ["production"]})

        assert response.status_code == 200
        assert response.data["id"] == str(self.event2.event_id)

    def test_snuba_environment_oldest(self) -> None:
        url = f"/api/0/issues/{self.group.id}/events/oldest/"
        response = self.client.get(url, format="json", data={"environment": ["production"]})

        assert response.status_code == 200
        assert response.data["id"] == str(self.event2.event_id)

    def test_snuba_environment_event_id(self) -> None:
        url = f"/api/0/issues/{self.group.id}/events/{self.event2.event_id}/"
        response = self.client.get(url, format="json", data={"environment": ["production"]})

        assert response.status_code == 200
        assert response.data["id"] == str(self.event2.event_id)

    def test_simple_latest(self) -> None:
        url = f"/api/0/issues/{self.group.id}/events/latest/"
        response = self.client.get(url, format="json")
        assert response.status_code == 200
        assert response.data["eventID"] == str(self.event2.event_id)

    def test_simple_oldest(self) -> None:
        url = f"/api/0/issues/{self.group.id}/events/oldest/"
        response = self.client.get(url, format="json")

        assert response.status_code == 200
        assert response.data["id"] == str(self.event1.event_id)

    def test_simple_event_id(self) -> None:
        url = f"/api/0/issues/{self.group.id}/events/{self.event1.event_id}/"
        response = self.client.get(url, format="json")

        assert response.status_code == 200
        assert response.data["id"] == str(self.event1.event_id)

    def test_perf_issue_latest(self) -> None:
        event = self.create_performance_issue()
        url = f"/api/0/issues/{event.group.id}/events/latest/"
        response = self.client.get(url, format="json")
        assert response.status_code == 200
        assert response.data["eventID"] == event.event_id

    def test_perf_issue_oldest(self) -> None:
        event = self.create_performance_issue()
        url = f"/api/0/issues/{event.group.id}/events/oldest/"
        response = self.client.get(url, format="json")
        assert response.status_code == 200
        assert response.data["eventID"] == event.event_id

    def test_perf_issue_event_id(self) -> None:
        event = self.create_performance_issue()
        url = f"/api/0/issues/{event.group.id}/events/{event.event_id}/"
        response = self.client.get(url, format="json")
        assert response.status_code == 200
        assert response.data["eventID"] == event.event_id

    def test_invalid_query(self) -> None:
        event = self.create_performance_issue()
        url = f"/api/0/issues/{event.group.id}/events/{event.event_id}/"
        response = self.client.get(url, format="json", data={"query": "release.version:foobar"})
        assert response.status_code == 400
