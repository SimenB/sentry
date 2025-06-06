from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from django.urls import reverse
from requests import PreparedRequest

from sentry.identity.services.identity.model import RpcIdentity
from sentry.integrations.gitlab.blame import fetch_file_blames
from sentry.integrations.gitlab.utils import GitLabApiClientPath
from sentry.integrations.source_code_management.commit_context import (
    CommitContextClient,
    FileBlameInfo,
    SourceLineInfo,
)
from sentry.integrations.source_code_management.repository import RepositoryClient
from sentry.integrations.types import IntegrationProviderSlug
from sentry.models.pullrequest import PullRequest, PullRequestComment
from sentry.models.repository import Repository
from sentry.shared_integrations.client.proxy import IntegrationProxyClient
from sentry.shared_integrations.exceptions import ApiError, ApiUnauthorized
from sentry.silo.base import SiloMode, control_silo_function
from sentry.utils import metrics
from sentry.utils.http import absolute_uri

if TYPE_CHECKING:
    from sentry.integrations.gitlab.integration import GitlabIntegration

logger = logging.getLogger("sentry.integrations.gitlab")


class GitLabSetupApiClient(IntegrationProxyClient):
    """
    API Client that doesn't require an installation.
    This client is used during integration setup to fetch data
    needed to build installation metadata
    """

    integration_name = "gitlab_setup"

    def __init__(self, base_url: str, access_token: str, verify_ssl: bool):
        super().__init__(verify_ssl=verify_ssl)
        self.base_url = base_url
        self.token = access_token

    def build_url(self, path: str) -> str:
        path = GitLabApiClientPath.build_api_url(self.base_url, path)
        path = super().build_url(path=path)
        return path

    @control_silo_function
    def authorize_request(self, prepared_request: PreparedRequest) -> PreparedRequest:
        prepared_request.headers["Authorization"] = f"Bearer {self.token}"
        return prepared_request

    @control_silo_function
    def get_group(self, group):
        """Get a group based on `path` which is a slug.

        We need to URL quote because subgroups use `/` in their
        `id` and GitLab requires slugs to be URL encoded.
        """
        group = quote(group, safe="")
        path = GitLabApiClientPath.group.format(group=group)
        return self.get(path)


class GitLabApiClient(IntegrationProxyClient, RepositoryClient, CommitContextClient):
    def __init__(self, installation: GitlabIntegration):
        self.installation = installation
        verify_ssl = self.metadata["verify_ssl"]
        self.is_refreshing_token = False
        self.refreshed_identity: RpcIdentity | None = None
        self.base_url = self.metadata["base_url"]
        org_integration_id = installation.org_integration.id
        self.integration_name = IntegrationProviderSlug.GITLAB

        super().__init__(
            integration_id=installation.model.id,
            org_integration_id=org_integration_id,
            verify_ssl=verify_ssl,
        )

    @property
    def identity(self) -> RpcIdentity:
        if self.refreshed_identity:
            return self.refreshed_identity
        return self.installation.default_identity

    @property
    def metadata(self):
        return self.installation.model.metadata

    def build_url(self, path: str) -> str:
        path = GitLabApiClientPath.build_api_url(self.base_url, path)
        path = super().build_url(path=path)
        return path

    @control_silo_function
    def authorize_request(self, prepared_request: PreparedRequest) -> PreparedRequest:
        access_token = self.identity.data["access_token"]
        prepared_request.headers["Authorization"] = f"Bearer {access_token}"
        return prepared_request

    def _refresh_auth(self):
        """
        Modeled after Doorkeeper's docs
        where Doorkeeper is a dependency for GitLab that handles OAuth

        https://github.com/doorkeeper-gem/doorkeeper/wiki/Enable-Refresh-Token-Credentials#testing-with-oauth2-gem
        """
        return self.identity.get_identity().refresh_identity(
            self.identity,
            refresh_token_url="{}{}".format(
                self.base_url.rstrip("/"), GitLabApiClientPath.oauth_token
            ),
            verify_ssl=self.metadata["verify_ssl"],
        )

    def request(self, *args: Any, **kwargs: Any):
        if SiloMode.get_current_mode() == SiloMode.REGION:
            # Skip token refreshes in Region silo, as these will
            # be handled below by the control silo when the
            # integration proxy invokes the client code.
            return super().request(*args, **kwargs)

        return self._issue_request_with_auto_token_refresh(*args, **kwargs)

    def _issue_request_with_auto_token_refresh(self, *args: Any, **kwargs: Any):
        try:
            response = super().request(*args, **kwargs)
        except ApiUnauthorized:
            if self.is_refreshing_token:
                raise
            return self._attempt_request_after_refreshing_token(*args, **kwargs)

        if (
            kwargs.get("raw_response", False)
            and response.status_code == 401
            and not self.is_refreshing_token
        ):
            # Because the caller may make the request with the raw_response
            # option, we need to manually check the response status code and
            # refresh the token if an auth error occurs.
            return self._attempt_request_after_refreshing_token(*args, **kwargs)

        return response

    def _attempt_request_after_refreshing_token(self, *args: Any, **kwargs: Any):
        assert not self.is_refreshing_token, "A token refresh is already occurring"
        self.is_refreshing_token = True
        self.refreshed_identity = self._refresh_auth()

        response = super().request(*args, **kwargs)

        self.is_refreshing_token = False
        self.refreshed_identity = None

        return response

    def get_user(self):
        """Get a user

        See https://docs.gitlab.com/ee/api/users.html#single-user
        """
        return self.get(GitLabApiClientPath.user)

    def search_projects(self, group=None, query=None, simple=True):
        """Get projects

        See https://docs.gitlab.com/ee/api/groups.html#list-a-group-s-projects
        and https://docs.gitlab.com/ee/api/projects.html#list-all-projects
        """

        def gen_params(page_number, page_size):
            # Simple param returns limited fields for the project.
            # Really useful, because we often don't need most of the project information
            params = {
                "search": query,
                "simple": simple,
                "order_by": "last_activity_at",
                "page": page_number + 1,  # page starts at 1
                "per_page": page_size,
            }
            if group:
                extra_params = {"include_subgroups": self.metadata.get("include_subgroups", False)}
            else:
                extra_params = {"membership": True}

            params.update(extra_params)
            return params

        def get_results(resp):
            return resp

        if group:
            path = GitLabApiClientPath.group_projects.format(group=group)
        else:
            path = GitLabApiClientPath.projects

        return self.get_with_pagination(path, gen_params, get_results)

    def get_project(self, project_id):
        """Get project

        See https://docs.gitlab.com/ee/api/projects.html#get-single-project
        """
        return self.get(GitLabApiClientPath.project.format(project=project_id))

    def get_issue(self, project_id, issue_id):
        """Get an issue

        See https://docs.gitlab.com/ee/api/issues.html#single-issue
        """
        try:
            return self.get(GitLabApiClientPath.issue.format(project=project_id, issue=issue_id))
        except IndexError:
            raise ApiError("Issue not found with ID", 404)

    def create_issue(self, project, data):
        """Create an issue

        See https://docs.gitlab.com/ee/api/issues.html#new-issue
        """
        return self.post(GitLabApiClientPath.issues.format(project=project), data=data)

    def create_comment(self, repo: str, issue_id: str, data: dict[str, Any]):
        """Create an issue note/comment

        See https://docs.gitlab.com/ee/api/notes.html#create-new-issue-note
        """
        return self.post(
            GitLabApiClientPath.create_issue_note.format(project=repo, issue_id=issue_id), data=data
        )

    def update_comment(self, repo: str, issue_id: str, comment_id: str, data: dict[str, Any]):
        """Modify existing issue note

        See https://docs.gitlab.com/ee/api/notes.html#modify-existing-issue-note
        """
        return self.put(
            GitLabApiClientPath.update_issue_note.format(
                project=repo, issue_id=issue_id, note_id=comment_id
            ),
            data=data,
        )

    def create_pr_comment(self, repo: Repository, pr: PullRequest, data: dict[str, Any]) -> Any:
        project_id = repo.config["project_id"]
        url = GitLabApiClientPath.create_pr_note.format(project=project_id, pr_key=pr.key)
        return self.post(url, data=data)

    def update_pr_comment(
        self,
        repo: Repository,
        pr: PullRequest,
        pr_comment: PullRequestComment,
        data: dict[str, Any],
    ) -> Any:
        project_id = repo.config["project_id"]
        url = GitLabApiClientPath.update_pr_note.format(
            project=project_id, pr_key=pr.key, note_id=pr_comment.external_id
        )
        return self.put(url, data=data)

    def search_project_issues(self, project_id, query, iids=None):
        """Search issues in a project

        See https://docs.gitlab.com/ee/api/issues.html#list-project-issues
        """
        path = GitLabApiClientPath.project_issues.format(project=project_id)

        return self.get(path, params={"scope": "all", "search": query, "iids": iids})

    def create_project_webhook(self, project_id):
        """Create a webhook on a project

        See https://docs.gitlab.com/ee/api/projects.html#add-project-hook
        """
        path = GitLabApiClientPath.project_hooks.format(project=project_id)
        hook_uri = reverse("sentry-extensions-gitlab-webhook")
        model = self.installation.model
        data = {
            "url": absolute_uri(hook_uri),
            "token": "{}:{}".format(model.external_id, model.metadata["webhook_secret"]),
            "merge_requests_events": True,
            "push_events": True,
            "enable_ssl_verification": model.metadata["verify_ssl"],
        }
        resp = self.post(path, data=data)

        return resp["id"]

    def delete_project_webhook(self, project_id, hook_id):
        """Delete a webhook from a project

        See https://docs.gitlab.com/ee/api/projects.html#delete-project-hook
        """
        path = GitLabApiClientPath.project_hook.format(project=project_id, hook_id=hook_id)
        return self.delete(path)

    def get_last_commits(self, project_id, end_sha):
        """Get the last set of commits ending at end_sha

        Gitlab doesn't give us a good way to do this, so we fetch the end_sha
        and use its date to find the block of commits. We only fetch one page
        of commits to match other implementations (github, bitbucket)

        See https://docs.gitlab.com/ee/api/commits.html#get-a-single-commit and
        https://docs.gitlab.com/ee/api/commits.html#list-repository-commits
        """
        path = GitLabApiClientPath.commit.format(project=project_id, sha=end_sha)
        commit = self.get(path)
        if not commit:
            return []
        end_date = commit["created_at"]

        path = GitLabApiClientPath.commits.format(project=project_id)
        return self.get(path, params={"until": end_date})

    def get_commit(self, project_id, sha):
        """
        Get the details of a commit
        See https://docs.gitlab.com/ee/api/commits.html#get-a-single-commit
        """
        return self.get_cached(GitLabApiClientPath.commit.format(project=project_id, sha=sha))

    def get_merge_commit_sha_from_commit(self, repo: Repository, sha: str) -> str | None:
        """
        Get the merge commit sha from a commit sha
        See https://docs.gitlab.com/api/commits/#list-merge-requests-associated-with-a-commit
        """
        project_id = repo.config["project_id"]
        path = GitLabApiClientPath.commit_merge_requests.format(project=project_id, sha=sha)
        response = self.get(path)

        # Filter out non-merged merge requests
        merge_requests = []
        for merge_request in response:
            if merge_request["state"] == "merged":
                merge_requests.append(merge_request)

        if len(merge_requests) != 1:
            # the response should return a single merged PR, returning None if multiple
            return None

        merge_request = merge_requests[0]
        return merge_request["merge_commit_sha"] or merge_request["squash_commit_sha"]

    def compare_commits(self, project_id, start_sha, end_sha):
        """Compare commits between two SHAs

        See https://docs.gitlab.com/ee/api/repositories.html#compare-branches-tags-or-commits
        """
        path = GitLabApiClientPath.compare.format(project=project_id)
        return self.get(path, params={"from": start_sha, "to": end_sha})

    def get_diff(self, project_id, sha):
        """Get the diff for a commit

        See https://docs.gitlab.com/ee/api/commits.html#get-the-diff-of-a-commit
        """
        path = GitLabApiClientPath.diff.format(project=project_id, sha=sha)
        return self.get(path)

    def check_file(self, repo: Repository, path: str, version: str | None) -> object | None:
        """Fetch a file for stacktrace linking

        See https://docs.gitlab.com/ee/api/repository_files.html#get-file-from-repository
        Path requires file path and ref
        file_path must also be URL encoded Ex. lib%2Fclass%2Erb
        """
        project_id = repo.config["project_id"]
        encoded_path = quote(path, safe="")

        request_path = GitLabApiClientPath.file.format(project=project_id, path=encoded_path)

        # Gitlab can return 404 or 400 if the file doesn't exist
        return self.head_cached(request_path, params={"ref": version})

    def get_file(
        self, repo: Repository, path: str, ref: str | None, codeowners: bool = False
    ) -> str:
        """Get the contents of a file

        See https://docs.gitlab.com/ee/api/repository_files.html#get-file-from-repository
        Path requires file path and ref
        file_path must also be URL encoded Ex. lib%2Fclass%2Erb
        """

        project_id = repo.config["project_id"]
        encoded_path = quote(path, safe="")
        request_path = GitLabApiClientPath.file_raw.format(project=project_id, path=encoded_path)

        contents = self.get(request_path, params={"ref": ref}, raw_response=True)
        result = contents.content.decode("utf-8")

        return result

    def get_blame_for_files(
        self, files: Sequence[SourceLineInfo], extra: Mapping[str, Any]
    ) -> list[FileBlameInfo]:
        metrics.incr("sentry.integrations.gitlab.get_blame_for_files")
        return fetch_file_blames(
            self,
            files,
            extra={
                **extra,
                "provider": IntegrationProviderSlug.GITLAB.value,
                "org_integration_id": self.org_integration_id,
            },
        )

    def get_pr_diffs(self, repo: Repository, pr: PullRequest) -> list[dict[str, Any]]:
        project_id = repo.config["project_id"]
        path = GitLabApiClientPath.build_pr_diffs(project=project_id, pr_key=pr.key, unidiff=True)
        return self.get(path)
