from typing import Any

from django.http import HttpResponse
from django.http.request import HttpRequest
from django.http.response import HttpResponseBase

from sentry.identity.base import Provider
from sentry.identity.pipeline import IdentityPipeline
from sentry.identity.services.identity.model import RpcIdentity
from sentry.pipeline.views.base import PipelineView
from sentry.users.models.identity import Identity

__all__ = ("DummyProvider",)


class AskEmail:
    def dispatch(self, request: HttpRequest, pipeline: IdentityPipeline) -> HttpResponseBase:
        if "email" in request.POST:
            pipeline.bind_state("email", request.POST.get("email"))
            return pipeline.next_step()

        return HttpResponse(DummyProvider.TEMPLATE)


class DummyProvider(Provider):
    name = "Dummy"
    key = "dummy"

    TEMPLATE = '<form method="POST"><input type="email" name="email" /></form>'

    def get_pipeline_views(self) -> list[PipelineView[IdentityPipeline]]:
        return [AskEmail()]

    def build_identity(self, state):
        return {"id": state["email"], "email": state["email"], "name": "Dummy"}

    def refresh_identity(self, identity: Identity | RpcIdentity, **kwargs: Any) -> None:
        pass
