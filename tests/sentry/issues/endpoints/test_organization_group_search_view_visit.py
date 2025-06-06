from django.urls import reverse
from django.utils import timezone

from sentry.models.groupsearchviewlastvisited import GroupSearchViewLastVisited
from sentry.testutils.helpers.datetime import freeze_time
from tests.sentry.issues.endpoints.test_organization_group_search_views import (
    GroupSearchViewAPITestCase,
)


class OrganizationGroupSearchViewVisitTest(GroupSearchViewAPITestCase):
    endpoint = "sentry-api-0-organization-group-search-view-visit"
    method = "post"

    def setUp(self) -> None:
        self.login_as(user=self.user)
        self.view = self.create_view(self.user)

        self.url = reverse(
            "sentry-api-0-organization-group-search-view-visit",
            kwargs={"organization_id_or_slug": self.organization.slug, "view_id": self.view.id},
        )

    @freeze_time("2025-03-03 14:52:37")
    def test_update_last_visited_success(self) -> None:
        assert (
            GroupSearchViewLastVisited.objects.filter(
                organization=self.organization,
                user_id=self.user.id,
                group_search_view=self.view,
            ).count()
            == 0
        )

        response = self.client.post(self.url)
        assert response.status_code == 204

        # Verify the last_visited record was created
        visited_view = GroupSearchViewLastVisited.objects.get(
            organization=self.organization,
            user_id=self.user.id,
            group_search_view=self.view,
        )
        assert visited_view.last_visited == timezone.now()

    @freeze_time("2025-03-03 14:52:37")
    def test_update_existing_last_visited(self) -> None:
        # Create an initial last_visited record with an old timestamp
        with freeze_time("2025-02-03 14:52:37"):
            GroupSearchViewLastVisited.objects.create(
                organization=self.organization,
                user_id=self.user.id,
                group_search_view=self.view,
                last_visited=timezone.now(),
            )

        # Update the last_visited timestamp
        response = self.client.post(self.url)
        assert response.status_code == 204

        # Verify the last_visited record was updated
        visited_view = GroupSearchViewLastVisited.objects.get(
            organization=self.organization,
            user_id=self.user.id,
            group_search_view=self.view,
        )
        assert visited_view.last_visited == timezone.now()
        assert visited_view.last_visited.year == 2025  # Verify it's the new timestamp
        assert visited_view.last_visited.month == 3
        assert visited_view.last_visited.day == 3
        assert visited_view.last_visited.hour == 14
        assert visited_view.last_visited.minute == 52
        assert visited_view.last_visited.second == 37

    def test_update_nonexistent_view(self) -> None:
        nonexistent_id = "99999"
        url = reverse(
            "sentry-api-0-organization-group-search-view-visit",
            kwargs={"organization_id_or_slug": self.organization.slug, "view_id": nonexistent_id},
        )

        response = self.client.post(url)
        assert response.status_code == 404

    def test_update_view_from_another_user(self) -> None:
        user_two = self.create_user()
        self.create_member(organization=self.organization, user=user_two)

        # Get a view ID from user_two
        view = self.create_view(user_two)
        url = reverse(
            "sentry-api-0-organization-group-search-view-visit",
            kwargs={"organization_id_or_slug": self.organization.slug, "view_id": view.id},
        )

        # This should succeed because the view exists in the organization
        # and the endpoint only checks if the view exists in the organization
        response = self.client.post(url)
        assert response.status_code == 204

        # Verify the last_visited record was created for the current user
        visited_view = GroupSearchViewLastVisited.objects.get(
            organization=self.organization,
            user_id=self.user.id,
            group_search_view=view,
        )
        assert visited_view is not None
