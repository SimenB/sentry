from unittest import mock

import pytest
import responses

from sentry.auth.providers.github.client import GitHubClient
from sentry.auth.providers.github.constants import API_DOMAIN


@pytest.fixture
def client():
    return GitHubClient("accessToken")


@responses.activate
def test_request_sends_access_token(client) -> None:
    responses.add(responses.GET, f"https://{API_DOMAIN}/", json={"status": "SUCCESS"}, status=200)
    client._request("/")

    assert len(responses.calls) == 1
    assert responses.calls[0].request.headers["Authorization"] == "token accessToken"


@mock.patch.object(GitHubClient, "_request")
def test_get_org_list(mock_request, client) -> None:
    client.get_org_list()
    mock_request.assert_called_once_with("/user/orgs")


@mock.patch.object(GitHubClient, "_request")
def test_get_user(mock_request, client) -> None:
    client.get_user()
    mock_request.assert_called_once_with("/user")


@mock.patch.object(GitHubClient, "_request")
def test_get_user_emails(mock_request, client) -> None:
    client.get_user_emails()
    mock_request.assert_called_once_with("/user/emails")


@mock.patch.object(GitHubClient, "_request", return_value=[{"id": 1396951}])
def test_is_org_member(mock_request, client) -> None:
    got = client.is_org_member(1396951)
    assert got is True
