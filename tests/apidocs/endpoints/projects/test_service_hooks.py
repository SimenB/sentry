from django.test.client import RequestFactory
from django.urls import reverse

from fixtures.apidocs_test_case import APIDocsTestCase


class ProjectServiceHooksDocs(APIDocsTestCase):
    def setUp(self):
        self.create_service_hook(project=self.project, events=("event.created",))
        self.create_service_hook(project=self.project, events=("event.alert",))

        self.url = reverse(
            "sentry-api-0-service-hooks",
            kwargs={
                "organization_id_or_slug": self.organization.slug,
                "project_id_or_slug": self.project.slug,
            },
        )

        self.login_as(user=self.user)

    def test_get(self) -> None:
        with self.feature("projects:servicehooks"):
            response = self.client.get(self.url)
        request = RequestFactory().get(self.url)

        self.validate_schema(request, response)

    def test_post(self) -> None:
        data = {"url": "https://example.com/other-sentry-hook", "events": ["event.created"]}
        with self.feature("projects:servicehooks"):
            response = self.client.post(self.url, data)
        request = RequestFactory().post(self.url, data)

        self.validate_schema(request, response)
