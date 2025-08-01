from sentry.constants import DS_DENYLIST
from sentry.testutils.cases import APITestCase, SnubaTestCase
from sentry.testutils.helpers.datetime import before_now


class ProjectTagsTest(APITestCase, SnubaTestCase):
    endpoint = "sentry-api-0-project-tags"

    def setUp(self):
        super().setUp()
        self.login_as(user=self.user)

    def test_simple(self) -> None:
        self.store_event(
            data={
                "tags": {"foo": "oof", "bar": "rab"},
                "timestamp": before_now(minutes=1).isoformat(),
            },
            project_id=self.project.id,
        )
        self.store_event(
            data={"tags": {"bar": "rab2"}, "timestamp": before_now(minutes=1).isoformat()},
            project_id=self.project.id,
        )

        response = self.get_success_response(self.project.organization.slug, self.project.slug)

        data = {v["key"]: v for v in response.data}
        assert len(data) == 3

        assert data["foo"]["canDelete"]
        assert data["foo"]["uniqueValues"] == 1
        assert data["bar"]["canDelete"]
        assert data["bar"]["uniqueValues"] == 2

    def test_simple_without_values_seen(self) -> None:
        self.store_event(
            data={
                "tags": {"foo": "oof", "bar": "rab"},
                "timestamp": before_now(minutes=1).isoformat(),
            },
            project_id=self.project.id,
        )
        self.store_event(
            data={"tags": {"bar": "rab2"}, "timestamp": before_now(minutes=1).isoformat()},
            project_id=self.project.id,
        )

        response = self.get_success_response(
            self.project.organization.slug, self.project.slug, includeValuesSeen=0
        )

        data = {v["key"]: v for v in response.data}
        assert len(data) == 3

        assert data["foo"]["canDelete"]
        assert "uniqueValues" not in data["foo"]
        assert data["bar"]["canDelete"]
        assert "uniqueValues" not in data["bar"]

    def test_simple_flags(self) -> None:
        self.store_event(
            data={
                "contexts": {
                    "flags": {
                        "values": [
                            {"flag": "abc", "result": True},
                            {"flag": "def", "result": False},
                        ]
                    }
                },
                "timestamp": before_now(minutes=1).isoformat(),
            },
            project_id=self.project.id,
        )
        self.store_event(
            data={
                "contexts": {
                    "flags": {
                        "values": [
                            {"flag": "abc", "result": False},
                        ]
                    }
                },
                "timestamp": before_now(minutes=1).isoformat(),
            },
            project_id=self.project.id,
        )

        response = self.get_success_response(
            self.project.organization.slug, self.project.slug, useFlagsBackend="1"
        )

        data = {v["key"]: v for v in response.data}
        assert len(data) == 2

        assert data["def"]["canDelete"] is False
        assert data["def"]["uniqueValues"] == 1
        assert data["abc"]["canDelete"] is False
        assert data["abc"]["uniqueValues"] == 2

    def test_simple_remove_tags_in_denylist(self) -> None:
        self.store_event(
            data={
                # "browser" and "sentry:dist" are in denylist sentry.constants.DS_DENYLIST
                "tags": {"browser": "chrome", "bar": "rab", "sentry:dist": "test_dist"},
                "timestamp": before_now(minutes=1).isoformat(),
            },
            project_id=self.project.id,
        )
        self.store_event(
            data={"tags": {"bar": "rab2"}, "timestamp": before_now(minutes=1).isoformat()},
            project_id=self.project.id,
        )

        response = self.get_success_response(
            self.project.organization.slug, self.project.slug, onlySamplingTags=1
        )

        data = {v["key"]: v for v in response.data}
        assert len(data) == 1

        assert data["bar"]["canDelete"]
        assert data["bar"]["uniqueValues"] == 2

    def test_simple_remove_tags_in_denylist_remove_all_tags(self) -> None:
        self.store_event(
            data={
                "tags": {deny_tag: "value_{deny_tag}" for deny_tag in DS_DENYLIST},
                "timestamp": before_now(minutes=1).isoformat(),
            },
            project_id=self.project.id,
        )
        response = self.get_success_response(
            self.project.organization.slug, self.project.slug, onlySamplingTags=1
        )

        data = {v["key"]: v for v in response.data}
        assert len(data) == 0
        assert data == {}
