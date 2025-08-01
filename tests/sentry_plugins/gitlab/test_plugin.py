from functools import cached_property

import orjson
import responses
from django.test import RequestFactory
from django.urls import reverse

from sentry.testutils.cases import PluginTestCase
from sentry_plugins.gitlab.plugin import GitLabPlugin


def test_conf_key() -> None:
    assert GitLabPlugin().conf_key == "gitlab"


class GitLabPluginTest(PluginTestCase):
    @cached_property
    def plugin(self):
        return GitLabPlugin()

    @cached_property
    def request(self):
        return RequestFactory()

    def test_get_issue_label(self) -> None:
        group = self.create_group(message="Hello world", culprit="foo.bar")
        assert self.plugin.get_issue_label(group, 1) == "GL-1"

    def test_get_issue_url(self) -> None:
        self.plugin.set_option("gitlab_url", "https://gitlab.com", self.project)
        self.plugin.set_option("gitlab_repo", "getsentry/sentry", self.project)
        group = self.create_group(message="Hello world", culprit="foo.bar")
        assert (
            self.plugin.get_issue_url(group, group.id)
            == "https://gitlab.com/getsentry/sentry/issues/%s" % group.id
        )

    def test_is_configured(self) -> None:
        assert self.plugin.is_configured(self.project) is False
        self.plugin.set_option("gitlab_url", "https://gitlab.com", self.project)
        assert self.plugin.is_configured(self.project) is False
        self.plugin.set_option("gitlab_repo", "getsentry/sentry", self.project)
        assert self.plugin.is_configured(self.project) is False
        self.plugin.set_option("gitlab_token", "abcdefg", self.project)
        assert self.plugin.is_configured(self.project) is True

    @responses.activate
    def test_create_issue(self) -> None:
        responses.add(
            responses.POST,
            "https://gitlab.com/api/v4/projects/getsentry%2Fsentry/issues",
            body='{"iid": 1, "id": "10"}',
        )

        self.plugin.set_option("gitlab_url", "https://gitlab.com", self.project)
        self.plugin.set_option("gitlab_repo", "getsentry/sentry", self.project)
        self.plugin.set_option("gitlab_token", "abcdefg", self.project)
        group = self.create_group(message="Hello world", culprit="foo.bar")

        request = self.request.get("/")
        request.user = self.user
        form_data = {"title": "Hello", "description": "Fix this."}

        self.login_as(self.user)

        assert self.plugin.create_issue(request, group, form_data) == 1
        request = responses.calls[0].request
        payload = orjson.loads(request.body)
        assert payload == {
            "title": "Hello",
            "description": "Fix this.",
            "labels": None,
            "assignee_id": None,
        }

    @responses.activate
    def test_link_issue(self) -> None:
        responses.add(
            responses.GET,
            "https://gitlab.com/api/v4/projects/getsentry%2Fsentry/issues/1",
            body='{"iid": 1, "id": "10", "title": "Hello world"}',
        )
        responses.add(
            responses.POST,
            "https://gitlab.com/api/v4/projects/getsentry%2Fsentry/issues/1/notes",
            body='{"body": "Hello"}',
        )

        self.plugin.set_option("gitlab_url", "https://gitlab.com", self.project)
        self.plugin.set_option("gitlab_repo", "getsentry/sentry", self.project)
        self.plugin.set_option("gitlab_token", "abcdefg", self.project)
        group = self.create_group(message="Hello world", culprit="foo.bar")

        request = self.request.get("/")
        request.user = self.user
        form_data = {"comment": "Hello", "issue_id": "1"}

        self.login_as(self.user)

        assert self.plugin.link_issue(request, group, form_data) == {"title": "Hello world"}
        request = responses.calls[-1].request
        payload = orjson.loads(request.body)
        assert payload == {"body": "Hello"}

    def test_no_secrets(self) -> None:
        self.user = self.create_user("foo@example.com")
        self.org = self.create_organization(owner=self.user, name="Rowdy Tiger")
        self.team = self.create_team(organization=self.org, name="Mariachi Band")
        self.project = self.create_project(organization=self.org, teams=[self.team], name="Bengal")
        self.login_as(self.user)
        self.plugin.set_option("gitlab_url", "https://gitlab.com", self.project)
        self.plugin.set_option("gitlab_repo", "getsentry/sentry", self.project)
        self.plugin.set_option("gitlab_token", "abcdefg", self.project)
        url = reverse(
            "sentry-api-0-project-plugin-details", args=[self.org.slug, self.project.slug, "gitlab"]
        )
        res = self.client.get(url)
        config = orjson.loads(res.content)["config"]
        token_config = [item for item in config if item["name"] == "gitlab_token"][0]
        assert token_config.get("type") == "secret"
        assert token_config.get("value") is None
        assert token_config.get("hasSavedValue") is True
        assert token_config.get("prefix") == "abcd"
