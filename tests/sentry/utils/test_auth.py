from datetime import timedelta

from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.base import SessionBase
from django.http import HttpRequest
from django.urls import reverse

import sentry.utils.auth
from sentry.testutils.cases import TestCase
from sentry.testutils.silo import control_silo_test
from sentry.users.models.user import User
from sentry.utils.auth import (
    EmailAuthBackend,
    SsoSession,
    construct_link_with_query,
    get_login_redirect,
    login,
)


@control_silo_test
class EmailAuthBackendTest(TestCase):
    def setUp(self) -> None:
        self.user = User(username="foo", email="baz@example.com")
        self.user.set_password("bar")
        self.user.save()

    @property
    def backend(self):
        return EmailAuthBackend()

    def test_can_authenticate_with_username(self) -> None:
        result = self.backend.authenticate(HttpRequest(), username="foo", password="bar")
        self.assertEqual(result, self.user)

    def test_can_authenticate_with_username_case_insensitive(self) -> None:
        result = self.backend.authenticate(HttpRequest(), username="FOO", password="bar")
        self.assertEqual(result, self.user)

    def test_can_authenticate_with_email(self) -> None:
        result = self.backend.authenticate(
            HttpRequest(), username="baz@example.com", password="bar"
        )
        self.assertEqual(result, self.user)

    def test_can_authenticate_with_email_case_insensitive(self) -> None:
        result = self.backend.authenticate(
            HttpRequest(), username="BAZ@example.com", password="bar"
        )
        self.assertEqual(result, self.user)

    def test_does_not_authenticate_with_invalid_password(self) -> None:
        result = self.backend.authenticate(HttpRequest(), username="foo", password="pizza")
        self.assertEqual(result, None)


@control_silo_test
class GetLoginRedirectTest(TestCase):
    def _make_request(self, next=None):
        request = HttpRequest()
        request.META["SERVER_NAME"] = "testserver"
        request.META["SERVER_PORT"] = "80"
        request.session = SessionBase()
        request.user = self.user
        if next:
            request.session["_next"] = next
        return request

    def test_schema_uses_default(self) -> None:
        result = get_login_redirect(self._make_request("http://example.com"))
        assert result == reverse("sentry-login")

        result = get_login_redirect(self._make_request("ftp://testserver"))
        assert result == reverse("sentry-login")

    def test_next(self) -> None:
        result = get_login_redirect(self._make_request("http://testserver/foobar/"))
        assert result == "http://testserver/foobar/"

        result = get_login_redirect(self._make_request("ftp://testserver/foobar/"))
        assert result == reverse("sentry-login")

        request = self._make_request("/foobar/")
        request.subdomain = "orgslug"
        result = get_login_redirect(request)
        assert result == "http://orgslug.testserver/foobar/"

        request = self._make_request("http://testserver/foobar/")
        request.subdomain = "orgslug"
        result = get_login_redirect(request)
        assert result == "http://testserver/foobar/"

        request = self._make_request("ftp://testserver/foobar/")
        request.subdomain = "orgslug"
        result = get_login_redirect(request)
        assert result == f"http://orgslug.testserver{reverse('sentry-login')}"

    def test_after_2fa(self) -> None:
        request = self._make_request()
        request.session["_after_2fa"] = "http://testserver/foobar/"
        result = get_login_redirect(request)
        assert result == "http://testserver/foobar/"

        request = self._make_request()
        request.subdomain = "orgslug"
        request.session["_after_2fa"] = "/foobar/"
        result = get_login_redirect(request)
        assert result == "http://orgslug.testserver/foobar/"

    def test_pending_2fa(self) -> None:
        request = self._make_request()
        request.session["_pending_2fa"] = [1234, 1234, 1234]
        result = get_login_redirect(request)
        assert result == reverse("sentry-2fa-dialog")

        request = self._make_request()
        request.subdomain = "orgslug"
        request.session["_pending_2fa"] = [1234, 1234, 1234]
        result = get_login_redirect(request)
        assert result == f"http://orgslug.testserver{reverse('sentry-2fa-dialog')}"

    def test_login_uses_default(self) -> None:
        result = get_login_redirect(self._make_request(reverse("sentry-login")))
        assert result == reverse("sentry-login")

    def test_no_value_uses_default(self) -> None:
        result = get_login_redirect(self._make_request())
        assert result == reverse("sentry-login")

        request = self._make_request()
        request.subdomain = "orgslug"
        result = get_login_redirect(request)
        assert result == f"http://orgslug.testserver{reverse('sentry-login')}"


@control_silo_test
class LoginTest(TestCase):
    def _make_request(self):
        request = HttpRequest()
        request.META["REMOTE_ADDR"] = "127.0.0.1"
        request.session = self.session
        request.user = AnonymousUser()
        return request

    def test_simple(self) -> None:
        request = self._make_request()
        assert login(request, self.user)
        assert request.user == self.user
        assert "_nonce" not in request.session

    def test_with_organization(self) -> None:
        org = self.create_organization(name="foo", owner=self.user)
        request = self._make_request()
        assert login(request, self.user, organization_id=org.id)
        assert request.user == self.user
        assert f"{SsoSession.SSO_SESSION_KEY}:{org.id}" in request.session

    def test_with_nonce(self) -> None:
        self.user.refresh_session_nonce()
        self.user.save()
        assert self.user.session_nonce is not None
        request = self._make_request()
        assert login(request, self.user)
        assert request.user == self.user
        assert request.session["_nonce"] == self.user.session_nonce


def test_sso_expiry_default() -> None:
    value = sentry.utils.auth._sso_expiry_from_env(None)
    # make sure no accidental changes affect sso timeout
    assert value == timedelta(days=7)


def test_sso_expiry_from_env() -> None:
    value = sentry.utils.auth._sso_expiry_from_env("20")
    assert value == timedelta(seconds=20)


def test_construct_link_with_query() -> None:
    # testing basic query param construction
    path = "foobar"
    query_params = {"biz": "baz"}
    expected_path = "foobar?biz=baz"

    assert construct_link_with_query(path=path, query_params=query_params) == expected_path

    # testing no excess '?' appended if query params are empty
    path = "foobar"
    query_params = {}
    expected_path = "foobar"

    assert construct_link_with_query(path=path, query_params=query_params) == expected_path
