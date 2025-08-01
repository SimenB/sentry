from __future__ import annotations

import contextlib
from unittest.mock import MagicMock, patch

import sentry_sdk.scope
from django.conf import settings
from django.db import OperationalError
from django.http import HttpRequest
from rest_framework.request import Request
from sentry_sdk import Scope

from sentry.models.organization import Organization
from sentry.testutils.cases import TestCase
from sentry.utils import sdk
from sentry.utils.sdk import (
    bind_ambiguous_org_context,
    bind_organization_context,
    capture_exception_with_scope_check,
    check_current_scope_transaction,
    check_tag_for_scope_bleed,
    merge_context_into_scope,
)


@contextlib.contextmanager
def patch_isolation_scope():
    """
    Generates and yields new Scope object, and patches sentry.utils.sdk.Scope.get_isolation_scope to return the same
    scope within the context manager.
    """
    scope = Scope(ty=sentry_sdk.scope.ScopeType.ISOLATION)
    with patch("sentry.utils.sdk.Scope.get_isolation_scope") as mock_get_isolation_scope:
        mock_get_isolation_scope.return_value = scope

        yield scope


class SDKUtilsTest(TestCase):
    def test_context_scope_merge_no_existing_context(self) -> None:
        scope = Scope()
        new_context_data = {"maisey": "silly", "charlie": "goofy"}

        assert "dogs" not in scope._contexts

        merge_context_into_scope("dogs", new_context_data, scope)

        assert "dogs" in scope._contexts
        assert scope._contexts["dogs"] == new_context_data

    def test_context_scope_merge_with_existing_context(self) -> None:
        scope = Scope()
        existing_context_data = {"cory": "nudgy", "bodhi": "floppy"}
        new_context_data = {"maisey": "silly", "charlie": "goofy"}
        scope.set_context("dogs", existing_context_data)

        assert "dogs" in scope._contexts

        merge_context_into_scope("dogs", new_context_data, scope)

        assert scope._contexts["dogs"] == {
            "cory": "nudgy",
            "bodhi": "floppy",
            "maisey": "silly",
            "charlie": "goofy",
        }


@patch("sentry.utils.sdk.logger.warning")
class CheckTagForScopeBleedTest(TestCase):
    def test_no_existing_tag(self, mock_logger_warning: MagicMock) -> None:
        with patch_isolation_scope() as mock_scope:
            mock_scope._tags = {}
            check_tag_for_scope_bleed("org.slug", "squirrel_chasers")

        assert "possible_mistag" not in mock_scope._tags
        assert "scope_bleed.tag.org.slug" not in mock_scope._tags
        assert "scope_bleed" not in mock_scope._contexts
        assert mock_logger_warning.call_count == 0

    def test_matching_existing_tag_single_org(self, mock_logger_warning: MagicMock) -> None:
        with patch_isolation_scope() as mock_scope:
            mock_scope._tags = {"org.slug": "squirrel_chasers"}
            check_tag_for_scope_bleed("org.slug", "squirrel_chasers")

        assert "possible_mistag" not in mock_scope._tags
        assert "scope_bleed.tag.org.slug" not in mock_scope._tags
        assert "scope_bleed" not in mock_scope._contexts
        assert mock_logger_warning.call_count == 0

    def test_matching_existing_tag_multiple_orgs(self, mock_logger_warning: MagicMock) -> None:
        # We don't bother to add the underlying slug list here, since right now it's not checked

        with patch_isolation_scope() as mock_scope:
            mock_scope._tags = {"organization.slug": "[multiple orgs]"}
            check_tag_for_scope_bleed("organization.slug", "[multiple orgs]")

        assert "possible_mistag" not in mock_scope._tags
        assert "scope_bleed.tag.organization.slug" not in mock_scope._tags
        assert "scope_bleed" not in mock_scope._contexts
        assert mock_logger_warning.call_count == 0

    def test_different_existing_tag_single_org(self, mock_logger_warning: MagicMock) -> None:
        with patch_isolation_scope() as mock_scope:
            mock_scope._tags = {"org.slug": "good_dogs"}
            check_tag_for_scope_bleed("org.slug", "squirrel_chasers")

        extra = {
            "previous_org.slug_tag": "good_dogs",
            "new_org.slug_tag": "squirrel_chasers",
        }
        assert "possible_mistag" in mock_scope._tags
        assert "scope_bleed.org.slug" in mock_scope._tags
        assert mock_scope._contexts["scope_bleed"] == extra
        mock_logger_warning.assert_called_with(
            "Tag already set and different (%s).", "org.slug", extra=extra
        )

    def test_different_existing_tag_incoming_is_multiple_orgs(
        self, mock_logger_warning: MagicMock
    ) -> None:
        with patch_isolation_scope() as mock_scope:
            mock_scope._tags = {"organization.slug": "good_dogs"}
            check_tag_for_scope_bleed("organization.slug", "[multiple orgs]")

        extra = {
            "previous_organization.slug_tag": "good_dogs",
            "new_organization.slug_tag": "[multiple orgs]",
        }
        assert "possible_mistag" in mock_scope._tags
        assert "scope_bleed.organization.slug" in mock_scope._tags
        assert mock_scope._contexts["scope_bleed"] == extra
        mock_logger_warning.assert_called_with(
            "Tag already set and different (%s).", "organization.slug", extra=extra
        )

    def test_getting_more_specific_doesnt_count_as_mismatch(
        self, mock_logger_warning: MagicMock
    ) -> None:
        orgs = [self.create_organization() for _ in range(3)]

        with patch_isolation_scope() as mock_scope:
            mock_scope.set_tag("organization.slug", "[multiple orgs]")
            mock_scope.set_tag("organization", "[multiple orgs]")
            mock_scope.set_context(
                "organization", {"multiple possible": [org.slug for org in orgs]}
            )
            check_tag_for_scope_bleed("organization.slug", orgs[1].slug)

        assert "possible_mistag" not in mock_scope._tags
        assert "scope_bleed.tag.organization.slug" not in mock_scope._tags
        assert "scope_bleed" not in mock_scope._contexts
        assert mock_logger_warning.call_count == 0

    def test_overwriting_list_with_non_member_single_org_counts_as_mismatch(
        self, mock_logger_warning: MagicMock
    ):
        orgs = [self.create_organization() for _ in range(3)]

        with patch_isolation_scope() as mock_scope:
            mock_scope.set_tag("organization.slug", "[multiple orgs]")
            mock_scope.set_tag("organization", "[multiple orgs]")
            mock_scope.set_context(
                "organization", {"multiple possible": [org.slug for org in orgs]}
            )
            check_tag_for_scope_bleed("organization.slug", "squirrel_chasers")

        extra = {
            "previous_organization.slug_tag": "[multiple orgs]",
            "new_organization.slug_tag": "squirrel_chasers",
        }
        assert "possible_mistag" in mock_scope._tags
        assert "scope_bleed.organization.slug" in mock_scope._tags
        assert mock_scope._contexts["scope_bleed"] == extra
        mock_logger_warning.assert_called_with(
            "Tag already set and different (%s).", "organization.slug", extra=extra
        )

    def test_add_to_scope_being_false(self, mock_logger_warning: MagicMock) -> None:
        with patch_isolation_scope() as mock_scope:
            mock_scope._tags = {"org.slug": "good_dogs"}
            check_tag_for_scope_bleed("org.slug", "squirrel_chasers", add_to_scope=False)

        extra = {
            "previous_org.slug_tag": "good_dogs",
            "new_org.slug_tag": "squirrel_chasers",
        }

        # no data added to scope, even though there's a mismatch
        assert "possible_mistag" not in mock_scope._tags
        assert "scope_bleed.tag.org.slug" not in mock_scope._tags
        assert "scope_bleed" not in mock_scope._contexts
        mock_logger_warning.assert_called_with(
            "Tag already set and different (%s).", "org.slug", extra=extra
        )

    def test_string_vs_int(self, mock_logger_warning: MagicMock) -> None:
        with patch_isolation_scope() as mock_scope:
            mock_scope._tags = {"org.id": "12311121"}
            check_tag_for_scope_bleed("org.id", 12311121)

        assert "possible_mistag" not in mock_scope._tags
        assert "scope_bleed.tag.org.id" not in mock_scope._tags
        assert "scope_bleed" not in mock_scope._contexts
        assert mock_logger_warning.call_count == 0

    def test_int_vs_string(self, mock_logger_warning: MagicMock) -> None:
        with patch_isolation_scope() as mock_scope:
            mock_scope._tags = {"org.id": 12311121}
            check_tag_for_scope_bleed("org.id", "12311121")

        assert "possible_mistag" not in mock_scope._tags
        assert "scope_bleed.tag.org.id" not in mock_scope._tags
        assert "scope_bleed" not in mock_scope._contexts
        assert mock_logger_warning.call_count == 0


class CheckScopeTransactionTest(TestCase):
    @patch("sentry.utils.sdk.LEGACY_RESOLVER.resolve", return_value="/dogs/{name}/")
    def test_scope_has_correct_transaction(self, mock_resolve: MagicMock) -> None:
        mock_scope = Scope()
        mock_scope._transaction = "/dogs/{name}/"

        with patch("sentry.utils.sdk.sentry_sdk.get_current_scope", return_value=mock_scope):
            mismatch = check_current_scope_transaction(Request(HttpRequest()))
            assert mismatch is None

    @patch("sentry.utils.sdk.LEGACY_RESOLVER.resolve", return_value="/dogs/{name}/")
    def test_scope_has_wrong_transaction(self, mock_resolve: MagicMock) -> None:
        mock_scope = Scope()
        mock_scope._transaction = "/tricks/{trick_name}/"

        with patch("sentry.utils.sdk.sentry_sdk.get_current_scope", return_value=mock_scope):
            mismatch = check_current_scope_transaction(Request(HttpRequest()))
            assert mismatch == {
                "scope_transaction": "/tricks/{trick_name}/",
                "request_transaction": "/dogs/{name}/",
            }

    @patch("sentry.utils.sdk.LEGACY_RESOLVER.resolve", return_value="/dogs/{name}/")
    def test_custom_transaction_name(self, mock_resolve: MagicMock) -> None:
        with patch_isolation_scope() as mock_scope:
            mock_scope._transaction = "/tricks/{trick_name}/"
            mock_scope._transaction_info["source"] = "custom"
            mismatch = check_current_scope_transaction(Request(HttpRequest()))
            # custom transaction names shouldn't be flagged even if they don't match
            assert mismatch is None


@patch("sentry_sdk.capture_exception")
class CaptureExceptionWithScopeCheckTest(TestCase):
    def test_passes_along_exception(self, mock_sdk_capture_exception: MagicMock) -> None:
        err = Exception()

        with patch("sentry.utils.sdk.check_current_scope_transaction", return_value=None):
            capture_exception_with_scope_check(err)

        assert mock_sdk_capture_exception.call_args.args[0] == err

    @patch("sentry.utils.sdk.check_current_scope_transaction")
    def test_doesnt_check_transaction_if_no_request(
        self,
        mock_check_transaction: MagicMock,
        mock_sdk_capture_exception: MagicMock,
    ):
        capture_exception_with_scope_check(Exception())

        assert mock_check_transaction.call_count == 0

    def test_no_transaction_mismatch(self, mock_sdk_capture_exception: MagicMock) -> None:
        with patch("sentry.utils.sdk.check_current_scope_transaction", return_value=None):
            capture_exception_with_scope_check(Exception(), request=Request(HttpRequest()))

        passed_scope = mock_sdk_capture_exception.call_args.kwargs["scope"]

        assert isinstance(passed_scope, Scope)
        assert "scope_bleed.transaction" not in passed_scope._tags
        assert "scope_bleed" not in passed_scope._contexts

    def test_with_transaction_mismatch(self, mock_sdk_capture_exception: MagicMock) -> None:
        scope_bleed_data = {
            "scope_transaction": "/tricks/{trick_name}/",
            "request_transaction": "/dogs/{name}/",
        }

        with patch(
            "sentry.utils.sdk.check_current_scope_transaction", return_value=scope_bleed_data
        ):
            capture_exception_with_scope_check(Exception(), request=Request(HttpRequest()))

        passed_scope = mock_sdk_capture_exception.call_args.kwargs["scope"]

        assert isinstance(passed_scope, Scope)
        assert passed_scope._tags["scope_bleed.transaction"] is True
        assert passed_scope._contexts["scope_bleed"] == scope_bleed_data

    def test_no_scope_data_passed(self, mock_sdk_capture_exception: MagicMock) -> None:
        capture_exception_with_scope_check(Exception())

        passed_scope = mock_sdk_capture_exception.call_args.kwargs["scope"]
        empty_scope = Scope(client=passed_scope.client)

        for entry in empty_scope.__slots__:
            # _propagation_context is generated on __init__ for tracing without performance
            # so is different every time. Same with client in SDK >=2.0.
            if entry in ("_propagation_context", "client"):
                continue
            # No new scope data should be passed
            assert getattr(passed_scope, entry) == getattr(empty_scope, entry)

    def test_passes_along_incoming_scope_object(
        self, mock_sdk_capture_exception: MagicMock
    ) -> None:
        incoming_scope_arg = Scope()

        capture_exception_with_scope_check(Exception(), scope=incoming_scope_arg)

        passed_scope = mock_sdk_capture_exception.call_args.kwargs["scope"]

        assert passed_scope == incoming_scope_arg

    def test_merges_incoming_scope_obj_and_args(
        self, mock_sdk_capture_exception: MagicMock
    ) -> None:
        incoming_scope_arg = Scope()
        incoming_scope_arg.set_level("info")

        capture_exception_with_scope_check(
            Exception(), scope=incoming_scope_arg, fingerprint="pawprint"
        )

        passed_scope = mock_sdk_capture_exception.call_args.kwargs["scope"]

        assert passed_scope._level == "info"
        assert passed_scope._fingerprint == "pawprint"

    def test_passes_along_incoming_scope_args(self, mock_sdk_capture_exception: MagicMock) -> None:
        capture_exception_with_scope_check(Exception(), fingerprint="pawprint")

        passed_scope = mock_sdk_capture_exception.call_args.kwargs["scope"]

        assert passed_scope._fingerprint == "pawprint"

    def test_doesnt_overwrite_incoming_scope_bleed_context(
        self, mock_sdk_capture_exception: MagicMock
    ):
        existing_scope_bleed_data = {
            "previous_org.slug_tag": "good_dogs",
            "new_org.slug_tag": "squirrel_chasers",
        }
        transaction_scope_bleed_data = {
            "scope_transaction": "/tricks/{trick_name}/",
            "request_transaction": "/dogs/{name}/",
        }
        incoming_scope_arg = Scope()
        incoming_scope_arg.set_context("scope_bleed", existing_scope_bleed_data)

        with patch(
            "sentry.utils.sdk.check_current_scope_transaction",
            return_value=transaction_scope_bleed_data,
        ):
            capture_exception_with_scope_check(
                Exception(), request=Request(HttpRequest()), scope=incoming_scope_arg
            )

        passed_scope = mock_sdk_capture_exception.call_args.kwargs["scope"]

        # both old and new data should be included
        assert "previous_org.slug_tag" in passed_scope._contexts["scope_bleed"]
        assert "new_org.slug_tag" in passed_scope._contexts["scope_bleed"]
        assert "scope_transaction" in passed_scope._contexts["scope_bleed"]
        assert "request_transaction" in passed_scope._contexts["scope_bleed"]


class BindOrganizationContextTest(TestCase):
    def setUp(self) -> None:
        self.org = self.create_organization()

    def test_simple(self) -> None:
        with patch_isolation_scope() as mock_scope:
            bind_organization_context(self.org)

            assert mock_scope._tags == {
                "organization": self.org.id,
                "organization.slug": self.org.slug,
            }
            assert mock_scope._contexts == {
                "organization": {
                    "id": self.org.id,
                    "slug": self.org.slug,
                }
            }

    def test_adds_values_from_context_helper(self) -> None:
        mock_context_helper = MagicMock(
            wraps=lambda scope, organization: scope.set_tag("organization.name", organization.name)
        )

        with patch_isolation_scope() as mock_scope:
            with patch.object(settings, "SENTRY_ORGANIZATION_CONTEXT_HELPER", mock_context_helper):
                bind_organization_context(self.org)

                assert mock_context_helper.call_count == 1
                assert mock_scope._tags == {
                    "organization": self.org.id,
                    "organization.slug": self.org.slug,
                    "organization.name": self.org.name,
                }

    def test_handles_context_helper_error(self) -> None:
        mock_context_helper = MagicMock(side_effect=Exception)

        with patch_isolation_scope() as mock_scope:
            with patch.object(settings, "SENTRY_ORGANIZATION_CONTEXT_HELPER", mock_context_helper):
                bind_organization_context(self.org)

                assert mock_context_helper.call_count == 1
                assert mock_scope._tags == {
                    "organization": self.org.id,
                    "organization.slug": self.org.slug,
                }


class BindAmbiguousOrgContextTest(TestCase):
    def _make_orgs(self, n: int) -> list[Organization]:
        return [self.create_organization() for _ in range(n)]

    def test_simple(self) -> None:
        orgs = self._make_orgs(3)

        with patch_isolation_scope() as mock_scope:
            bind_ambiguous_org_context(orgs, "integration id=1231")

            assert mock_scope._tags == {
                "organization": "[multiple orgs]",
                "organization.slug": "[multiple orgs]",
            }
            assert mock_scope._contexts == {
                "organization": {
                    "multiple possible": [org.slug for org in orgs],
                    "source": "integration id=1231",
                },
            }

    def test_doesnt_overwrite_org_in_list(self) -> None:
        orgs = self._make_orgs(3)
        single_org = orgs[2]
        expected_tags = {
            "organization": single_org.id,
            "organization.slug": single_org.slug,
        }
        expected_contexts = {
            "organization": {
                "id": single_org.id,
                "slug": single_org.slug,
            }
        }

        with patch_isolation_scope() as mock_scope:
            # First add data from a single org in our list
            bind_organization_context(single_org)

            assert mock_scope._tags == expected_tags
            assert mock_scope._contexts == expected_contexts

            # Now try to overwrite that with the whole list, which should be a no-op
            bind_ambiguous_org_context(orgs, "integration id=1231")

            assert mock_scope._tags == expected_tags
            assert mock_scope._contexts == expected_contexts

    def test_does_overwrite_org_not_in_list(self) -> None:
        other_org, *orgs = self._make_orgs(4)
        assert other_org.slug not in [org.slug for org in orgs]

        with patch_isolation_scope() as mock_scope:
            # First add data from a single org not in our list
            bind_organization_context(other_org)

            assert mock_scope._tags == {
                "organization": other_org.id,
                "organization.slug": other_org.slug,
            }

            # Now try to overwrite that with the whole list, which should work
            bind_ambiguous_org_context(orgs, "integration id=1231")

            assert mock_scope._tags == {
                "organization": "[multiple orgs]",
                "organization.slug": "[multiple orgs]",
                "possible_mistag": True,
                "scope_bleed.organization.slug": True,
            }
            assert mock_scope._contexts == {
                "organization": {
                    "multiple possible": [org.slug for org in orgs],
                    "source": "integration id=1231",
                },
                "scope_bleed": {
                    "previous_organization.slug_tag": other_org.slug,
                    "new_organization.slug_tag": "[multiple orgs]",
                },
            }

    def test_truncates_list(self) -> None:
        orgs = self._make_orgs(5)

        with patch.object(sdk, "_AMBIGUOUS_ORG_CUTOFF", 3), patch_isolation_scope() as mock_scope:
            bind_ambiguous_org_context(orgs, "integration id=1231")

            slug_list_in_org_context = mock_scope._contexts["organization"]["multiple possible"]
            assert len(slug_list_in_org_context) == 3
            assert slug_list_in_org_context[-1] == "... (3 more)"


def test_before_send_error_level() -> None:
    event = {
        "tags": {
            "silo_mode": "REGION",
            "sentry_region": "testregion456576",
        },
        "level": "error",
    }
    hint = {"exc_info": (OperationalError, OperationalError("test"), None)}
    event_with_before_send = sdk.before_send(event, hint)  # type: ignore[arg-type]
    assert event_with_before_send
    assert event_with_before_send["level"] == "warning"
