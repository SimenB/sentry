from uuid import uuid4

from sentry.testutils.cases import APITestCase

PROFILING_FEATURES = {"organizations:profiling": True}


class ProjectProfilingProfileTest(APITestCase):
    endpoint = "sentry-api-0-project-profiling-profile"

    def setUp(self) -> None:
        self.login_as(user=self.user)

    def test_feature_flag_disabled(self) -> None:
        response = self.get_response(self.project.organization.slug, self.project.id, str(uuid4()))
        assert response.status_code == 404
