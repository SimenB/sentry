import logging

from django.contrib import messages
from django.http import HttpRequest
from django.http.response import HttpResponseBase
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.request import Request

from sentry.auth.helper import AuthHelper
from sentry.auth.store import FLOW_LOGIN
from sentry.constants import WARN_SESSION_EXPIRED
from sentry.models.authprovider import AuthProvider
from sentry.organizations.services.organization import RpcOrganization, organization_service
from sentry.utils.auth import initiate_login
from sentry.web.frontend.auth_login import AuthLoginView

logger = logging.getLogger("sentry.saml_setup_error")


class AuthOrganizationLoginView(AuthLoginView):
    def respond_login(self, request: Request, context, *args, **kwargs) -> HttpResponseBase:
        return self.respond("sentry/organization-login.html", context)

    def handle_sso(self, request: HttpRequest, organization: RpcOrganization, auth_provider):
        if request.method == "POST":
            helper = AuthHelper(
                request=request,
                organization=organization,
                auth_provider=auth_provider,
                flow=FLOW_LOGIN,
                referrer=request.GET.get(
                    "referrer"
                ),  # TODO: get referrer from the form submit - not the query parms
            )

            if request.POST.get("init"):
                helper.initialize()

            if not helper.is_valid():
                logger.info(
                    "AuthOrganizationLoginView",
                    extra=helper.state.get_state(),
                )
                return helper.error("Something unexpected happened during authentication.")

            return helper.current_step()

        provider = auth_provider.get_provider()

        context = self.get_default_context(request, organization=organization) | {
            "provider_key": provider.key,
            "provider_name": provider.name,
            "authenticated": request.user.is_authenticated,
        }

        return self.respond("sentry/organization-login.html", context)

    @method_decorator(never_cache)
    def handle(self, request: HttpRequest, organization_slug) -> HttpResponseBase:
        org_context = organization_service.get_organization_by_slug(
            slug=organization_slug, only_visible=True
        )
        if org_context is None:
            return self.redirect(reverse("sentry-login"))
        organization = org_context.organization

        request.session.set_test_cookie()

        # check on POST to handle
        # multiple tabs case well now that we include redirect in url
        if request.method == "POST":
            referrer = None
            if request.session.get("_referrer") is not None:
                referrer = request.session.pop("_referrer")
            next_uri = self.get_next_uri(request)
            initiate_login(request, next_uri, referrer)

        try:
            auth_provider = AuthProvider.objects.get(organization_id=organization.id)
        except AuthProvider.DoesNotExist:
            auth_provider = None

        session_expired = "session_expired" in request.COOKIES
        if session_expired:
            messages.add_message(request, messages.WARNING, WARN_SESSION_EXPIRED)

        if not auth_provider:
            response = self.handle_basic_auth(request, organization=organization)
        else:
            response = self.handle_sso(request, organization, auth_provider)

        if session_expired:
            response.delete_cookie("session_expired")

        return response
