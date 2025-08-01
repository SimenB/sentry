import sentry_sdk
from rest_framework.request import Request
from rest_framework.response import Response

from sentry.api.api_publish_status import ApiPublishStatus
from sentry.api.base import region_silo_endpoint
from sentry.api.bases.organization import OrganizationEndpoint
from sentry.api.serializers import serialize
from sentry.api.serializers.models import OrganizationMemberWithProjectsSerializer
from sentry.models.organization import Organization
from sentry.models.organizationmember import OrganizationMember
from sentry.models.organizationmemberteam import OrganizationMemberTeam
from sentry.models.projectteam import ProjectTeam


@region_silo_endpoint
class OrganizationUsersEndpoint(OrganizationEndpoint):
    publish_status = {
        # Removing public documentation in favor of OrganizationMemberIndexEndpoint
        "GET": ApiPublishStatus.PRIVATE,
    }

    def get(self, request: Request, organization: Organization) -> Response:
        """
        List an Organization's Projects Users
        ````````````````````````````

        Return a list of users that belong to a given organization and are part of a project.

        :qparam string project: restrict results to users who have access to a given project ID
        :pparam string organization_id_or_slug: the id or slug of the organization for which the users
                                          should be listed.
        :auth: required
        """
        projects = self.get_projects(request, organization)

        with sentry_sdk.start_span(op="OrganizationUsersEndpoint.get_members") as span:
            qs = OrganizationMember.objects.filter(
                user_id__isnull=False,
                user_is_active=True,
                organization=organization,
                id__in=OrganizationMemberTeam.objects.filter(
                    team_id__in=ProjectTeam.objects.filter(project_id__in=projects)
                    .values_list("team_id", flat=True)
                    .distinct(),
                ).values_list("organizationmember_id", flat=True),
            ).order_by("user_email")

            organization_members = list(qs)

            span.set_data("Project Count", len(projects))
            span.set_data("Member Count", len(organization_members))

        return Response(
            serialize(
                organization_members,
                request.user,
                serializer=OrganizationMemberWithProjectsSerializer(
                    projects=projects,
                ),
            )
        )
