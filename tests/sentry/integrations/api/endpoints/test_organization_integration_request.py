from sentry.testutils.cases import APITestCase


class OrganizationIntegrationRequestTest(APITestCase):
    """Unit tests for emailing organization owners asking them to install an integration."""

    endpoint = "sentry-api-0-organization-integration-request"
    method = "post"

    def setUp(self) -> None:
        self.owner = self.user
        self.member = self.create_user(email="member@example.com")
        self.create_member(user=self.member, organization=self.organization, role="member")
        self.login_as(user=self.member)

    def test_integration_request(self) -> None:
        self.get_success_response(
            self.organization.slug,
            providerSlug="github",
            providerType="first_party",
        )

    def test_integration_request_with_invalid_plugin(self) -> None:
        self.get_error_response(
            self.organization.slug,
            providerSlug="ERROR",
            providerType="plugin",
            status_code=400,
        )

    def test_integration_request_with_invalid_sentryapp(self) -> None:
        self.get_error_response(
            self.organization.slug,
            providerSlug="ERROR",
            providerType="sentry_app",
            status_code=400,
        )

    def test_integration_request_with_invalid_integration(self) -> None:
        self.get_error_response(
            self.organization.slug,
            providerSlug="ERROR",
            providerType="first_party",
            status_code=400,
        )

    def test_integration_request_as_owner(self) -> None:
        self.login_as(user=self.owner)
        response = self.get_success_response(
            self.organization.slug,
            providerSlug="github",
            providerType="first_party",
        )
        assert response.data["detail"] == "User can install integration"

    def test_integration_request_without_permissions(self) -> None:
        self.login_as(user=self.create_user(email="nonmember@example.com"))
        self.get_error_response(
            self.organization.slug,
            providerSlug="github",
            providerType="first_party",
            status_code=403,
        )
