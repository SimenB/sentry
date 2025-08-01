from functools import cached_property
from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.test import RequestFactory

from sentry.middleware.health import HealthCheck
from sentry.status_checks import Problem
from sentry.utils import json


class HealthCheckTest(TestCase):
    middleware = cached_property(HealthCheck)

    @cached_property
    def factory(self):
        return RequestFactory()

    @patch("sentry.status_checks.check_all")
    def test_other_url(self, check_all: MagicMock) -> None:
        req = self.factory.get("/")
        resp = self.middleware.process_request(req)
        assert resp is None, resp
        assert check_all.call_count == 0

    @patch("sentry.status_checks.check_all")
    def test_basic_health(self, check_all: MagicMock) -> None:
        req = self.factory.get("/_health/")
        resp = self.middleware.process_request(req)
        assert resp.status_code == 200, resp
        assert check_all.call_count == 0

    @patch("sentry.status_checks.check_all")
    def test_full_health_ok(self, check_all: MagicMock) -> None:
        check_all.return_value = {object(): []}
        req = self.factory.get("/_health/?full")
        resp = self.middleware.process_request(req)
        assert resp.status_code == 200, resp
        body = json.loads(resp.content)
        assert "problems" in body
        assert "healthy" in body
        assert check_all.call_count == 1

    @patch("sentry.status_checks.check_all")
    def test_full_health_bad(self, check_all: MagicMock) -> None:
        check_all.return_value = {object(): [Problem("the system is down")]}
        req = self.factory.get("/_health/?full")
        resp = self.middleware.process_request(req)
        assert resp.status_code == 500, resp
        body = json.loads(resp.content)
        assert "problems" in body
        assert "healthy" in body
        assert check_all.call_count == 1
