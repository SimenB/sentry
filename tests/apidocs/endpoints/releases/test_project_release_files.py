from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.client import RequestFactory
from django.urls import reverse

from fixtures.apidocs_test_case import APIDocsTestCase


class ProjectReleaseFilesListDocsTest(APIDocsTestCase):
    def setUp(self):
        project = self.create_project(name="foo")
        file1 = self.create_file(
            name="blah.js",
            size=42,
            type="release.file",
            headers={"Content-Type": "application/json"},
            checksum="dc1e3f3e411979d336c3057cce64294f3420f93a",
        )
        release = self.create_release(project=project, version="1")

        self.create_release_file(
            file=file1, release_id=release.id, name="http://example.com/blah.js"
        )

        self.url = reverse(
            "sentry-api-0-project-release-files",
            kwargs={
                "project_id_or_slug": project.slug,
                "organization_id_or_slug": project.organization.slug,
                "version": release.version,
            },
        )

        self.login_as(user=self.user)

    def test_get(self) -> None:
        response = self.client.get(self.url)
        request = RequestFactory().get(self.url)

        self.validate_schema(request, response)

    def test_post(self) -> None:
        data = {
            "name": "http://example.com/application.js",
            "header": "X-SourceMap: http://example.com",
            "file": SimpleUploadedFile(
                "application.js", b"function() { }", content_type="application/javascript"
            ),
        }
        response = self.client.post(
            self.url,
            data,
            format="multipart",
        )
        request = RequestFactory().post(
            self.url,
            data=data,
            content_type="multipart/form-data",
            SERVER_NAME="us.sentry.io",
            secure=True,
        )

        self.validate_schema(request, response)
