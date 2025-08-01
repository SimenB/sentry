from sentry.testutils.cases import APITestCase


class UserOrganizationsTest(APITestCase):
    endpoint = "sentry-api-0-user-organizations"

    def setUp(self) -> None:
        super().setUp()
        self.login_as(self.user)

    def test_simple(self) -> None:
        organization_id = self.organization.id  # force creation

        response = self.get_success_response("me")
        assert len(response.data) == 1
        assert response.data[0]["id"] == str(organization_id)
