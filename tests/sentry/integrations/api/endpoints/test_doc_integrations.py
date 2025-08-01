from __future__ import annotations

from typing import Any

from rest_framework import status
from rest_framework.response import Response

from sentry.api.serializers.base import serialize
from sentry.integrations.models.doc_integration import DocIntegration
from sentry.integrations.models.integration_feature import IntegrationFeature, IntegrationTypes
from sentry.testutils.cases import APITestCase
from sentry.testutils.helpers.options import override_options
from sentry.testutils.silo import control_silo_test


class DocIntegrationsTest(APITestCase):
    endpoint = "sentry-api-0-doc-integrations"

    def setUp(self) -> None:
        self.user = self.create_user(email="jinx@lol.com")
        self.superuser = self.create_user(email="vi@lol.com", is_superuser=True)
        self.staff_user = self.create_user(is_staff=True)
        self.doc_1 = self.create_doc_integration(name="test_1", is_draft=False, has_avatar=True)
        self.doc_2 = self.create_doc_integration(name="test_2", is_draft=True, has_avatar=True)
        self.doc_3 = self.create_doc_integration(
            name="test_3",
            is_draft=False,
            metadata={"resources": [{"title": "Documentation", "url": "https://docs.sentry.io/"}]},
            features=[2, 3, 4],
        )

    def get_avatars(self, response: Response) -> list[Any]:
        return [doc.get("avatar") for doc in response.data]


@control_silo_test
class GetDocIntegrationsTest(DocIntegrationsTest):
    method = "GET"

    @override_options({"staff.ga-rollout": True})
    def test_staff_read_docs(self) -> None:
        """
        Tests that all DocIntegrations are returned for staff users,
        along with serialized versions of their avatars and IntegrationFeatures
        """
        self.login_as(user=self.staff_user, staff=True)
        response = self.get_success_response(status_code=status.HTTP_200_OK)
        assert len(response.data) == 3
        for doc in [self.doc_1, self.doc_2, self.doc_3]:
            assert serialize(doc) in response.data
        # Check that DocIntegrationAvatars were serialized
        for doc in [self.doc_1, self.doc_2]:
            assert doc.avatar.exists()
            assert serialize(doc.avatar.get()) in self.get_avatars(response)
        # Check that IntegrationFeatures were also serialized
        features = IntegrationFeature.objects.filter(
            target_id=self.doc_3.id, target_type=IntegrationTypes.DOC_INTEGRATION.value
        )
        for feature in features:
            assert serialize(feature) in serialize(self.doc_3)["features"]

    # TODO(schew2381): Change test to check superuser can only fetch non-draft DocIntegrations
    def test_superuser_read_docs(self) -> None:
        """
        Tests that all DocIntegrations are returned for super users,
        along with serialized versions of their avatars and IntegrationFeatures
        """
        self.login_as(user=self.superuser, superuser=True)
        response = self.get_success_response(status_code=status.HTTP_200_OK)
        assert len(response.data) == 3
        for doc in [self.doc_1, self.doc_2, self.doc_3]:
            assert serialize(doc) in response.data
        # Check that DocIntegrationAvatars were serialized
        for doc in [self.doc_1, self.doc_2]:
            assert doc.avatar.exists()
            assert serialize(doc.avatar.get()) in self.get_avatars(response)
        # Check that IntegrationFeatures were also serialized
        features = IntegrationFeature.objects.filter(
            target_id=self.doc_3.id, target_type=IntegrationTypes.DOC_INTEGRATION.value
        )
        for feature in features:
            assert serialize(feature) in serialize(self.doc_3)["features"]

    def test_read_docs_public(self) -> None:
        """
        Tests that only non-draft DocIntegrations are returned for users,
        along with serialized versions of their avatars and IntegrationFeatures
        """
        self.login_as(user=self.user)
        response = self.get_success_response(status_code=status.HTTP_200_OK)
        assert len(response.data) == 2
        for doc in [self.doc_1, self.doc_3]:
            assert serialize(doc) in response.data
        # Check that the DocIntegrationAvatar was serialized
        assert self.doc_1.avatar.exists()
        assert serialize(self.doc_1.avatar.get()) in self.get_avatars(response)
        # Check that IntegrationFeatures were also serialized
        features = IntegrationFeature.objects.filter(
            target_id=self.doc_3.id, target_type=IntegrationTypes.DOC_INTEGRATION.value
        )
        assert len(features) == 3
        for feature in features:
            assert serialize(feature) in serialize(self.doc_3)["features"]


@control_silo_test
class PostDocIntegrationsTest(DocIntegrationsTest):
    method = "POST"
    payload: dict[str, Any] = {
        "name": "Enemy",
        "author": "Imagine Dragons",
        "description": "An opening theme song 👀",
        "url": "https://github.com/getsentry/sentry/",
        "popularity": 5,
        "resources": [{"title": "Docs", "url": "https://github.com/getsentry/sentry/"}],
        "features": [1, 2, 3],
    }
    ignored_keys = ["is_draft", "metadata"]

    def setUp(self) -> None:
        super().setUp()
        self.login_as(user=self.staff_user, staff=True)

    def test_staff_create_doc(self) -> None:
        """
        Tests that a draft DocIntegration is created for superuser requests along
        with all the appropriate IntegrationFeatures
        """
        response = self.get_success_response(status_code=status.HTTP_201_CREATED, **self.payload)
        doc = DocIntegration.objects.get(name=self.payload["name"], author=self.payload["author"])
        assert serialize(doc) == response.data
        assert doc.is_draft
        features = IntegrationFeature.objects.filter(
            target_id=doc.id, target_type=IntegrationTypes.DOC_INTEGRATION.value
        )
        assert features.exists()
        assert len(features) == 3
        for feature in features:
            # Ensure payload features are in the database
            assert feature.feature in self.payload["features"]
            # Ensure they are also serialized in the response
            assert serialize(feature) in response.data["features"]

    # TODO(schew2381): Change test to check superuser can't access POST
    def test_superuser_create_doc(self) -> None:
        """
        Tests that a draft DocIntegration is created for superuser requests along
        with all the appropriate IntegrationFeatures
        """
        self.login_as(user=self.superuser, superuser=True)
        response = self.get_success_response(status_code=status.HTTP_201_CREATED, **self.payload)
        doc = DocIntegration.objects.get(name=self.payload["name"], author=self.payload["author"])
        assert serialize(doc) == response.data
        assert doc.is_draft
        features = IntegrationFeature.objects.filter(
            target_id=doc.id, target_type=IntegrationTypes.DOC_INTEGRATION.value
        )
        assert features.exists()
        assert len(features) == 3
        for feature in features:
            # Ensure payload features are in the database
            assert feature.feature in self.payload["features"]
            # Ensure they are also serialized in the response
            assert serialize(feature) in response.data["features"]

    def test_create_invalid_auth(self) -> None:
        """
        Tests that the POST endpoint is only accessible for superusers
        """
        self.login_as(user=self.user)
        self.get_error_response(status_code=status.HTTP_403_FORBIDDEN, **self.payload)

    def test_create_repeated_slug(self) -> None:
        """
        Tests that repeated names throw errors when generating slugs
        """
        payload = {**self.payload, "name": self.doc_1.name}
        response = self.get_error_response(status_code=status.HTTP_400_BAD_REQUEST, **payload)
        assert "name" in response.data.keys()

    def test_generated_slug_not_entirely_numeric(self) -> None:
        """
        Tests that generated slug based on name is not entirely numeric
        """
        payload = {**self.payload, "name": "1234"}
        response = self.get_success_response(status_code=status.HTTP_201_CREATED, **payload)

        slug = response.data["slug"]
        assert slug.startswith("1234-")
        assert not slug.isdecimal()

    def test_create_invalid_metadata(self) -> None:
        """
        Tests that incorrectly structured metadata throws an error
        """
        invalid_resources = {
            "not_an_array": {},
            "extra_keys": [{**self.payload["resources"][0], "extra": "key"}],
            "missing_keys": [{"title": "Missing URL field"}],
        }
        for resources in invalid_resources.values():
            payload = {**self.payload, "resources": resources}
            response = self.get_error_response(status_code=status.HTTP_400_BAD_REQUEST, **payload)
            assert "metadata" in response.data.keys()

    def test_create_empty_metadata(self) -> None:
        """
        Tests that sending no metadata keys does not trigger any
        server/database errors
        """
        payload = {**self.payload}
        del payload["resources"]
        response = self.get_success_response(status_code=status.HTTP_201_CREATED, **payload)
        assert "resources" not in response.data.keys()

    def test_create_ignore_keys(self) -> None:
        """
        Tests that certain reserved keys cannot be overridden by the
        request payload. They must be created by the API.
        """
        payload = {**self.payload, "is_draft": False, "metadata": {"should": "not override"}}
        self.get_success_response(status_code=status.HTTP_201_CREATED, **payload)
        doc = DocIntegration.objects.get(name=self.payload["name"], author=self.payload["author"])
        # Ensure the DocIntegration was not created with the ignored keys' values
        for key in self.ignored_keys:
            assert getattr(doc, key) is not payload[key]

    def test_create_duplicate_features(self) -> None:
        """
        Tests that providing duplicate keys do not result in a server
        error; instead, the excess are ignored.
        """
        payload = {**self.payload, "features": [0, 0, 0, 0, 1, 1, 1, 2]}
        self.get_success_response(status_code=status.HTTP_201_CREATED, **payload)
        doc = DocIntegration.objects.get(name=self.payload["name"], author=self.payload["author"])
        features = IntegrationFeature.objects.filter(
            target_id=doc.id, target_type=IntegrationTypes.DOC_INTEGRATION.value
        )
        assert features.exists()
        assert len(features) == 3
