from unittest import mock

import sentry.hybridcloud.rpc.caching as caching_module
from sentry.models.apiapplication import ApiApplication
from sentry.sentry_apps.models.sentry_app import SentryApp
from sentry.sentry_apps.models.sentry_app_installation import SentryAppInstallation
from sentry.testutils.cases import TestCase
from sentry.testutils.silo import control_silo_test
from sentry.types.region import get_region_for_organization


@control_silo_test
class SentryAppInstallationTest(TestCase):
    def setUp(self) -> None:
        self.user = self.create_user()
        self.proxy = self.create_user()
        self.org = self.create_organization()
        self.application = ApiApplication.objects.create(owner=self.proxy)

        self.sentry_app = SentryApp.objects.create(
            application=self.application,
            name="NullDB",
            proxy_user=self.proxy,
            owner_id=self.org.id,
            scope_list=("project:read",),
            webhook_url="http://example.com",
        )

        self.install = SentryAppInstallation(
            sentry_app=self.sentry_app, organization_id=self.org.id
        )

    def test_paranoid(self) -> None:
        self.install.save()
        self.install.delete()
        assert self.install.date_deleted is not None
        assert self.install not in SentryAppInstallation.objects.all()

    def test_date_updated(self) -> None:
        self.install.save()
        date_updated = self.install.date_updated
        self.install.save()
        assert not self.install.date_updated == date_updated

    def test_related_names(self) -> None:
        self.install.save()
        assert self.install in self.install.sentry_app.installations.all()
        assert self.install in SentryAppInstallation.objects.filter(
            organization_id=self.install.organization_id
        )

    def test_handle_async_replication_clears_region_cache(self) -> None:
        with mock.patch.object(caching_module, "region_caching_service") as mock_caching_service:
            self.install.save()
            region = get_region_for_organization(self.org.slug)
            mock_caching_service.clear_key.assert_any_call(
                key=f"app_service.get_installation:{self.install.id}", region_name=region.name
            )
