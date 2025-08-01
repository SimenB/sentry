from sentry.integrations.models.integration_feature import IntegrationFeature, IntegrationTypes
from sentry.testutils.cases import TestCase
from sentry.testutils.silo import control_silo_test


@control_silo_test
class IntegrationFeatureTest(TestCase):
    def setUp(self) -> None:
        self.sentry_app = self.create_sentry_app()
        self.integration_feature = IntegrationFeature.objects.get(
            target_id=self.sentry_app.id, target_type=IntegrationTypes.SENTRY_APP.value
        )

    def test_feature_str(self) -> None:
        assert self.integration_feature.feature_str() == "integrations-api"

    def test_description(self) -> None:
        assert (
            self.integration_feature.description
            == "%s can **utilize the Sentry API** to pull data or update resources in Sentry (with permissions granted, of course)."
            % self.sentry_app.name
        )

        self.integration_feature.user_description = "Custom description"
        self.integration_feature.save()
        assert self.integration_feature.description == "Custom description"
