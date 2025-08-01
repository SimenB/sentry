from sentry.testutils.cases import APITestCase


class ProjectTeamsTest(APITestCase):
    endpoint = "sentry-api-0-project-teams"

    def setUp(self) -> None:
        super().setUp()
        self.login_as(self.user)

    def test_simple(self) -> None:
        team = self.create_team()
        project = self.create_project(teams=[team])

        response = self.get_success_response(project.organization.slug, project.slug)

        assert len(response.data) == 1
        assert response.data[0]["slug"] == team.slug
        assert response.data[0]["name"] == team.name
