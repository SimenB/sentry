from __future__ import annotations

import orjson
from requests.exceptions import RequestException

from sentry import http

from .constants import API_DOMAIN


class GitHubApiError(Exception):
    def __init__(self, message="", status=0) -> None:
        super().__init__(message)
        self.status = status


class GitHubClient:
    def __init__(self, access_token) -> None:
        self.http = http.build_session()
        self.access_token = access_token

    def __enter__(self) -> GitHubClient:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.http.close()

    def _request(self, path: str):
        headers = {"Authorization": f"token {self.access_token}"}

        try:
            req = self.http.get(
                f"https://{API_DOMAIN}/{path.lstrip('/')}",
                headers=headers,
            )
        except RequestException as e:
            raise GitHubApiError(f"{e}", status=getattr(e, "status_code", 0))
        if req.status_code < 200 or req.status_code >= 300:
            raise GitHubApiError(req.content, status=req.status_code)
        return orjson.loads(req.content)

    def get_org_list(self):
        return self._request("/user/orgs")

    def get_user(self):
        return self._request("/user")

    def get_user_emails(self):
        return self._request("/user/emails")

    def is_org_member(self, org_id) -> bool:
        org_id = str(org_id)
        for o in self.get_org_list():
            if str(o["id"]) == org_id:
                return True
        return False
