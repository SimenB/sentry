from django.test.client import RequestFactory
from django.urls import reverse

from fixtures.apidocs_test_case import APIDocsTestCase


class ReleaseFileDetailsDocsTest(APIDocsTestCase):
    def setUp(self):
        self.login_as(user=self.user)

        project = self.create_project(name="foo")
        release = self.create_release(project=project, version="1")
        file1 = self.create_file(
            name="blah.js",
            size=42,
            type="release.file",
            headers={"Content-Type": "application/json"},
            checksum="dc1e3f3e411979d336c3057cce64294f3420f93a",
        )
        releasefile = self.create_release_file(
            file=file1, release_id=release.id, name="http://example.com/blah.js"
        )

        self.url = reverse(
            "sentry-api-0-organization-release-file-details",
            kwargs={
                "organization_id_or_slug": project.organization.slug,
                "version": release.version,
                "file_id": releasefile.id,
            },
        )

    def test_get(self) -> None:
        response = self.client.get(self.url)
        request = RequestFactory().get(self.url)

        self.validate_schema(request, response)

    def test_put(self) -> None:
        data = {"name": "newfilename.js"}
        response = self.client.put(self.url, data)
        request = RequestFactory().put(self.url, data)

        self.validate_schema(request, response)
