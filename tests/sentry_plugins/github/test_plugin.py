from functools import cached_property

import orjson
import pytest
import responses
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from sentry.exceptions import PluginError
from sentry.testutils.cases import PluginTestCase
from sentry_plugins.github.plugin import GitHubPlugin


def test_conf_key() -> None:
    assert GitHubPlugin().conf_key == "github"


class GitHubPluginTest(PluginTestCase):
    @cached_property
    def plugin(self):
        return GitHubPlugin()

    @cached_property
    def request(self):
        return RequestFactory()

    def test_get_issue_label(self) -> None:
        group = self.create_group(message="Hello world", culprit="foo.bar")
        assert self.plugin.get_issue_label(group, 1) == "GH-1"

    def test_get_issue_url(self) -> None:
        self.plugin.set_option("repo", "getsentry/sentry", self.project)
        group = self.create_group(message="Hello world", culprit="foo.bar")
        assert self.plugin.get_issue_url(group, 1) == "https://github.com/getsentry/sentry/issues/1"

    def test_is_configured(self) -> None:
        assert self.plugin.is_configured(self.project) is False
        self.plugin.set_option("repo", "getsentry/sentry", self.project)
        assert self.plugin.is_configured(self.project) is True

    @responses.activate
    def test_create_issue(self) -> None:
        responses.add(
            responses.POST,
            "https://api.github.com/repos/getsentry/sentry/issues",
            json={"number": 1, "title": "Hello world"},
        )

        self.plugin.set_option("repo", "getsentry/sentry", self.project)
        group = self.create_group(message="Hello world", culprit="foo.bar")

        request = self.request.get("/")
        request.user = AnonymousUser()
        form_data = {"title": "Hello", "description": "Fix this."}
        with pytest.raises(PluginError):
            self.plugin.create_issue(request, group, form_data)

        request.user = self.user
        self.login_as(self.user)
        self.create_usersocialauth(
            user=self.user, provider=self.plugin.auth_provider, extra_data={"access_token": "foo"}
        )

        assert self.plugin.create_issue(request, group, form_data) == 1
        request = responses.calls[0].request
        assert request.headers["Authorization"] == "Bearer foo"
        payload = orjson.loads(request.body)
        assert payload == {"title": "Hello", "body": "Fix this.", "assignee": None}

    @responses.activate
    def test_link_issue(self) -> None:
        responses.add(
            responses.GET,
            "https://api.github.com/repos/getsentry/sentry/issues/1",
            json={"number": 1, "title": "Hello world"},
        )
        responses.add(
            responses.POST,
            "https://api.github.com/repos/getsentry/sentry/issues/1/comments",
            json={"body": "Hello"},
        )

        self.plugin.set_option("repo", "getsentry/sentry", self.project)
        group = self.create_group(message="Hello world", culprit="foo.bar")

        request = self.request.get("/")
        request.user = AnonymousUser()
        form_data = {"comment": "Hello", "issue_id": "1"}
        with pytest.raises(PluginError):
            self.plugin.link_issue(request, group, form_data)

        request.user = self.user
        self.login_as(self.user)
        self.create_usersocialauth(
            user=self.user, provider=self.plugin.auth_provider, extra_data={"access_token": "foo"}
        )

        assert self.plugin.link_issue(request, group, form_data) == {"title": "Hello world"}
        request = responses.calls[-1].request
        assert request.headers["Authorization"] == "Bearer foo"
        payload = orjson.loads(request.body)
        assert payload == {"body": "Hello"}
