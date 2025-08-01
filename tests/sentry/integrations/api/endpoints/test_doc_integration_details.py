from __future__ import annotations

from typing import Any

import pytest
from rest_framework import status

from sentry.api.serializers.base import serialize
from sentry.integrations.models.doc_integration import DocIntegration
from sentry.integrations.models.integration_feature import IntegrationFeature, IntegrationTypes
from sentry.testutils.cases import APITestCase
from sentry.testutils.silo import control_silo_test


class DocIntegrationDetailsTest(APITestCase):
    endpoint = "sentry-api-0-doc-integration-details"

    def setUp(self) -> None:
        self.user = self.create_user(email="jinx@lol.com")
        self.superuser = self.create_user(email="vi@lol.com", is_superuser=True)
        self.staff_user = self.create_user(is_staff=True)
        self.doc_1 = self.create_doc_integration(name="test_1", is_draft=True, has_avatar=False)
        self.doc_2 = self.create_doc_integration(
            name="test_2",
            is_draft=False,
            metadata={"resources": [{"title": "Documentation", "url": "https://docs.sentry.io/"}]},
            features=[2, 3, 4],
            has_avatar=True,
        )
        self.doc_delete = self.create_doc_integration(
            name="test_3", is_draft=True, features=[1, 2, 3, 4, 5, 6, 7], has_avatar=True
        )


@control_silo_test
class GetDocIntegrationDetailsTest(DocIntegrationDetailsTest):
    method = "GET"

    def test_staff_read_doc(self) -> None:
        """
        Tests that any DocIntegration is visible (with all the expected data)
        for those with superuser permissions
        """
        self.login_as(user=self.staff_user, staff=True)
        # Non-draft DocIntegration, with features and an avatar
        response = self.get_success_response(self.doc_2.slug, status_code=status.HTTP_200_OK)
        assert serialize(self.doc_2) == response.data
        features = IntegrationFeature.objects.filter(
            target_id=self.doc_2.id, target_type=IntegrationTypes.DOC_INTEGRATION.value
        )
        for feature in features:
            assert serialize(feature) in response.data["features"]
        assert serialize(self.doc_2.avatar.get()) == response.data["avatar"]
        # Draft DocIntegration, without features or an avatar
        response = self.get_success_response(self.doc_1.slug, status_code=status.HTTP_200_OK)
        assert serialize(self.doc_1) == response.data
        assert not response.data["avatar"]

    # TODO(schew2381): Change test to check that superusers can only fetch non-draft DocIntegrations
    def test_superuser_read_doc(self) -> None:
        """
        Tests that any DocIntegration is visible (with all the expected data)
        for those with superuser permissions
        """
        self.login_as(user=self.superuser, superuser=True)
        # Non-draft DocIntegration, with features and an avatar
        response = self.get_success_response(self.doc_2.slug, status_code=status.HTTP_200_OK)
        assert serialize(self.doc_2) == response.data
        features = IntegrationFeature.objects.filter(
            target_id=self.doc_2.id, target_type=IntegrationTypes.DOC_INTEGRATION.value
        )
        for feature in features:
            assert serialize(feature) in response.data["features"]
        assert serialize(self.doc_2.avatar.get()) == response.data["avatar"]
        # Draft DocIntegration, without features or an avatar
        response = self.get_success_response(self.doc_1.slug, status_code=status.HTTP_200_OK)
        assert serialize(self.doc_1) == response.data
        assert not response.data["avatar"]

    def test_public_read_doc(self) -> None:
        """
        Tests that only non-draft DocIntegrations (with all the expected data)
        are visible for those without superuser permissions
        """
        self.login_as(user=self.user)
        # Non-draft DocIntegration, with features and an avatar
        response = self.get_success_response(self.doc_2.slug, status_code=status.HTTP_200_OK)
        assert serialize(self.doc_2) == response.data
        features = IntegrationFeature.objects.filter(
            target_id=self.doc_2.id, target_type=IntegrationTypes.DOC_INTEGRATION.value
        )
        for feature in features:
            assert serialize(feature) in serialize(self.doc_2)["features"]
        assert serialize(self.doc_2.avatar.get()) == response.data["avatar"]
        # Draft DocIntegration, without features or an avatar
        self.get_error_response(self.doc_1.slug, status_code=status.HTTP_403_FORBIDDEN)


@control_silo_test
class PutDocIntegrationDetailsTest(DocIntegrationDetailsTest):
    method = "PUT"
    payload: dict[str, Any] = {
        "name": "Enemy",
        "author": "Imagine Dragons",
        "description": "An opening theme song 👀",
        "url": "https://github.com/getsentry/sentry/",
        "popularity": 5,
        "resources": [{"title": "Docs", "url": "https://github.com/getsentry/sentry/"}],
        "features": [4, 5, 6],
        "is_draft": False,
    }
    ignored_keys = ["metadata"]

    def setUp(self) -> None:
        super().setUp()
        self.login_as(user=self.staff_user, staff=True)

    def test_staff_update_doc(self) -> None:
        """
        Tests that a DocIntegration can be updated by superuser requests
        """
        response = self.get_success_response(
            self.doc_2.slug, status_code=status.HTTP_200_OK, **self.payload
        )
        self.doc_2.refresh_from_db()
        assert serialize(self.doc_2) == response.data
        features = IntegrationFeature.objects.filter(
            target_id=self.doc_2.id, target_type=IntegrationTypes.DOC_INTEGRATION.value
        )
        assert features.exists()
        assert len(features) == 3
        for feature in features:
            # Ensure payload features are in the database
            assert feature.feature in self.payload["features"]
            # Ensure they are also serialized in the response
            assert serialize(feature) in response.data["features"]

    # TODO(schew2381): Change test to check that superusers cannot update DocIntegrations
    def test_superuser_update_doc(self) -> None:
        """
        Tests that a DocIntegration can be updated by superuser requests
        """
        self.login_as(user=self.superuser, superuser=True)
        response = self.get_success_response(
            self.doc_2.slug, status_code=status.HTTP_200_OK, **self.payload
        )
        self.doc_2.refresh_from_db()
        assert serialize(self.doc_2) == response.data
        features = IntegrationFeature.objects.filter(
            target_id=self.doc_2.id, target_type=IntegrationTypes.DOC_INTEGRATION.value
        )
        assert features.exists()
        assert len(features) == 3
        for feature in features:
            # Ensure payload features are in the database
            assert feature.feature in self.payload["features"]
            # Ensure they are also serialized in the response
            assert serialize(feature) in response.data["features"]

    def test_update_invalid_auth(self) -> None:
        """
        Tests that non-superuser PUT requests to the endpoint are ignored and
        have no side-effects on the database records
        """
        self.login_as(user=self.user)
        self.get_error_response(
            self.doc_1.slug, status_code=status.HTTP_403_FORBIDDEN, **self.payload
        )

    def test_update_removes_unused_features(self) -> None:
        """
        Tests that DocIntegration updates remove any unused and no longer
        necessary features from the database
        """
        self.get_success_response(self.doc_2.slug, status_code=status.HTTP_200_OK, **self.payload)
        unused_features = IntegrationFeature.objects.filter(
            target_id=self.doc_2.id,
            target_type=IntegrationTypes.DOC_INTEGRATION.value,
        ).exclude(feature__in=self.payload["features"])
        assert not unused_features.exists()

    def test_update_retains_carryover_features(self) -> None:
        """
        Tests that DocIntegration updates retain any existing features if
        applicable to avoid pointless database transactions
        """
        unaffected_feature = IntegrationFeature.objects.get(
            target_id=self.doc_2.id, target_type=IntegrationTypes.DOC_INTEGRATION.value, feature=4
        )
        initial_date_added = unaffected_feature.date_added
        self.get_success_response(self.doc_2.slug, status_code=status.HTTP_200_OK, **self.payload)
        unaffected_feature.refresh_from_db()
        assert initial_date_added == unaffected_feature.date_added

    def test_update_duplicate_features(self) -> None:
        """
        Tests that providing duplicate keys do not result in a server
        error; instead, the excess are ignored.
        """
        payload = {**self.payload, "features": [0, 0, 0, 0, 1, 1, 1, 2]}
        self.get_success_response(self.doc_2.slug, status_code=status.HTTP_200_OK, **payload)
        features = IntegrationFeature.objects.filter(
            target_id=self.doc_2.id, target_type=IntegrationTypes.DOC_INTEGRATION.value
        )
        assert features.exists()
        assert len(features) == 3

    def test_update_does_not_change_slug(self) -> None:
        """
        Tests that a name alteration is permitted and does not have an
        effect on the slug of the DocIntegration
        """
        previous_slug = self.doc_2.slug
        self.get_success_response(self.doc_2.slug, status_code=status.HTTP_200_OK, **self.payload)
        self.doc_2.refresh_from_db()
        assert self.doc_2.slug == previous_slug

    def test_update_invalid_metadata(self) -> None:
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
            response = self.get_error_response(
                self.doc_2.slug, status_code=status.HTTP_400_BAD_REQUEST, **payload
            )
            assert "metadata" in response.data.keys()

    def test_update_empty_metadata(self) -> None:
        """
        Tests that sending no metadata keys should erase any existing
        metadata contained on the record
        """
        previous_metadata = self.doc_2.metadata
        payload = {**self.payload}
        del payload["resources"]
        response = self.get_success_response(
            self.doc_2.slug, status_code=status.HTTP_200_OK, **payload
        )
        assert "resources" not in response.data.keys()
        self.doc_2.refresh_from_db()
        assert self.doc_2.metadata != previous_metadata

    def test_update_ignore_keys(self) -> None:
        """
        Tests that certain reserved keys cannot be overridden by the
        request payload. They must be created by the API.
        """
        payload = {**self.payload, "metadata": {"should": "not override"}}
        self.get_success_response(self.doc_2.slug, status_code=status.HTTP_200_OK, **payload)
        # Ensure the DocIntegration was not created with the ignored keys' values
        for key in self.ignored_keys:
            assert getattr(self.doc_2, key) is not payload[key]

    def test_update_simple_without_avatar(self) -> None:
        """
        Tests that the DocIntegration can be edited without an
        associated DocIntegrationAvatar.
        """
        payload = {**self.payload, "is_draft": True}
        response = self.get_success_response(
            self.doc_1.slug, status_code=status.HTTP_200_OK, **payload
        )
        self.doc_1.refresh_from_db()
        assert serialize(self.doc_1) == response.data

    def test_update_publish_without_avatar(self) -> None:
        """
        Tests that the DocIntegration cannot be published without an
        associated DocIntegrationAvatar.
        """
        response = self.get_error_response(
            self.doc_1.slug, status_code=status.HTTP_400_BAD_REQUEST, **self.payload
        )
        assert "avatar" in response.data.keys()
        avatar = self.create_doc_integration_avatar(doc_integration=self.doc_1)
        response = self.get_success_response(
            self.doc_1.slug, status_code=status.HTTP_200_OK, **self.payload
        )
        self.doc_1.refresh_from_db()
        assert serialize(self.doc_1) == response.data
        assert serialize(avatar) == response.data["avatar"]


@control_silo_test
class DeleteDocIntegrationDetailsTest(DocIntegrationDetailsTest):
    method = "DELETE"

    def test_staff_delete_valid(self) -> None:
        """
        Tests that the delete method works for those with superuser
        permissions, deleting the DocIntegration and associated
        IntegrationFeatures and DocIntegrationAvatar
        """
        self.login_as(user=self.staff_user, staff=True)
        features = IntegrationFeature.objects.filter(
            target_id=self.doc_delete.id, target_type=IntegrationTypes.DOC_INTEGRATION.value
        )
        assert features.exists()
        assert self.doc_delete.avatar.exists()
        self.get_success_response(self.doc_delete.slug, status_code=status.HTTP_204_NO_CONTENT)
        with pytest.raises(DocIntegration.DoesNotExist):
            DocIntegration.objects.get(id=self.doc_delete.id)
        assert not features.exists()
        assert not self.doc_delete.avatar.exists()

    # TODO(schew2381): Change test to check that superusers cannot delete DocIntegrations
    def test_superuser_delete_valid(self) -> None:
        """
        Tests that the delete method works for those with superuser
        permissions, deleting the DocIntegration and associated
        IntegrationFeatures and DocIntegrationAvatar
        """
        self.login_as(user=self.superuser, superuser=True)
        features = IntegrationFeature.objects.filter(
            target_id=self.doc_delete.id, target_type=IntegrationTypes.DOC_INTEGRATION.value
        )
        assert features.exists()
        assert self.doc_delete.avatar.exists()
        self.get_success_response(self.doc_delete.slug, status_code=status.HTTP_204_NO_CONTENT)
        with pytest.raises(DocIntegration.DoesNotExist):
            DocIntegration.objects.get(id=self.doc_delete.id)
        assert not features.exists()
        assert not self.doc_delete.avatar.exists()

    def test_public_delete_invalid(self) -> None:
        """
        Tests that the delete method is not accessible by those with regular member
        permissions, and no changes occur in the database.
        """
        self.login_as(user=self.user)
        self.get_error_response(self.doc_delete.slug, status_code=status.HTTP_403_FORBIDDEN)
        assert DocIntegration.objects.get(id=self.doc_delete.id)
        features = IntegrationFeature.objects.filter(
            target_id=self.doc_delete.id, target_type=IntegrationTypes.DOC_INTEGRATION.value
        )
        assert features.exists()
        assert len(features) == 7
        assert self.doc_delete.avatar.exists()
