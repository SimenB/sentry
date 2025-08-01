from django.urls import reverse

from sentry.plugins.base import plugins
from sentry.testutils.cases import APITestCase


class OrganizationPluginsTest(APITestCase):
    def setUp(self) -> None:
        self.projectA = self.create_project()
        self.projectB = self.create_project(organization=self.projectA.organization)

        plugins.get("webhooks").enable(self.projectA)
        plugins.get("slack").enable(self.projectB)

        self.login_as(user=self.user)

    def test_exposes_all_plugins_available_no_enabled_state(self) -> None:
        url = reverse(
            "sentry-api-0-organization-plugins",
            kwargs={"organization_id_or_slug": self.projectA.organization.slug},
        )

        url = f"{url}?plugins=_all"

        response = self.client.get(url)

        assert response.status_code == 200, (response.status_code, response.content)

        # should have these plugins:
        # issuetrackingplugin2, webhooks, mail
        # none of the plugins should have an 'enabled' key since these
        # plugins are not bound by a project
        plugins = [p for p in [p for p in response.data if "enabled" in p]]
        assert len(plugins) == 0
        assert len(response.data) > 0

    def test_exposes_plugins_across_all_org_projects(self) -> None:
        url = reverse(
            "sentry-api-0-organization-plugins",
            kwargs={"organization_id_or_slug": self.projectA.organization.slug},
        )

        url = f"{url}?plugins=slack&plugins=webhooks"

        response = self.client.get(url)

        assert response.status_code == 200, (response.status_code, response.content)

        enabled_plugins = [
            (p["project"]["id"], p["slug"]) for p in [p for p in response.data if p["enabled"]]
        ]

        assert (self.projectA.id, "webhooks") in enabled_plugins
        assert (self.projectB.id, "slack") in enabled_plugins

    def test_exposes_specific_plugins_across_all_org_projects(self) -> None:
        url = reverse(
            "sentry-api-0-organization-plugins",
            kwargs={"organization_id_or_slug": self.projectA.organization.slug},
        )

        url = f"{url}?plugins=slack"
        response = self.client.get(url)

        assert response.status_code == 200, (response.status_code, response.content)

        enabled_plugins = [
            (p["project"]["id"], p["slug"]) for p in [p for p in response.data if p["enabled"]]
        ]

        assert (self.projectA.id, "webhooks") not in enabled_plugins
        assert (self.projectB.id, "slack") in enabled_plugins

    def test_ignore_plugins_that_dont_exist(self) -> None:
        url = reverse(
            "sentry-api-0-organization-plugins",
            kwargs={"organization_id_or_slug": self.projectA.organization.slug},
        )

        url = f"{url}?plugins=nope&plugins=beep&plugins=slack"
        response = self.client.get(url)

        assert response.status_code == 200, (response.status_code, response.content)

        enabled_plugins = [
            (p["project"]["id"], p["slug"]) for p in [p for p in response.data if p["enabled"]]
        ]

        assert enabled_plugins == [(self.projectB.id, "slack")]
