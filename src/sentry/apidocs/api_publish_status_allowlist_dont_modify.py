"""
This list is tracking old api endpoints that we couldn't decide publish status for.
The goal is to eventually find owners for all and shrink this list.
DO NOT ADD ANY NEW APIS
"""

API_PUBLISH_STATUS_ALLOWLIST_DONT_MODIFY = {
    "/api/0/relays/": {"GET"},
    "/api/0/relays/register/challenge/": {"POST"},
    "/api/0/relays/register/response/": {"POST"},
    "/api/0/relays/projectconfigs/": {"POST"},
    "/api/0/relays/projectids/": {"POST"},
    "/api/0/relays/publickeys/": {"POST"},
    "/api/0/relays/live/": {"GET"},
    "/api/0/relays/{relay_id}/": {"DELETE"},
    "/api/0/{var}/{issue_id}/": {"DELETE", "GET", "PUT"},
    "/api/0/{var}/{issue_id}/activities/": {"GET"},
    "/api/0/{var}/{issue_id}/events/{event_id}/": {"GET"},
    "/api/0/{var}/{issue_id}/{var}/": {"GET", "POST"},
    "/api/0/{var}/{issue_id}/{var}/{note_id}/": {"DELETE", "PUT"},
    "/api/0/{var}/{issue_id}/hashes/": {"GET", "PUT"},
    "/api/0/{var}/{issue_id}/reprocessing/": {"POST"},
    "/api/0/{var}/{issue_id}/stats/": {"GET"},
    "/api/0/{var}/{issue_id}/tags/": {"GET"},
    "/api/0/{var}/{issue_id}/tags/{key}/values/": {"GET"},
    "/api/0/{var}/{issue_id}/attachments/": {"GET"},
    "/api/0/{var}/{issue_id}/similar/": {"GET"},
    "/api/0/{var}/{issue_id}/external-issues/": {"GET"},
    "/api/0/{var}/{issue_id}/external-issues/{external_issue_id}/": {"DELETE"},
    "/api/0/{var}/{issue_id}/integrations/": {"GET"},
    "/api/0/{var}/{issue_id}/integrations/{integration_id}/": {"DELETE", "GET", "PUT", "POST"},
    "/api/0/{var}/{issue_id}/current-release/": {"GET"},
    "/api/0/{var}/{issue_id}/first-last-release/": {"GET"},
    "/api/0/{var}/{issue_id}/plugins/asana/create/": {"GET", "POST"},
    "/api/0/{var}/{issue_id}/plugins/asana/link/": {"GET", "POST"},
    "/api/0/{var}/{issue_id}/plugins/asana/unlink/": {"GET", "POST"},
    "/api/0/{var}/{issue_id}/plugins/asana/autocomplete": {"GET", "POST"},
    "/api/0/{var}/{issue_id}/plugins/bitbucket/create/": {"GET", "POST"},
    "/api/0/{var}/{issue_id}/plugins/bitbucket/link/": {"GET", "POST"},
    "/api/0/{var}/{issue_id}/plugins/bitbucket/unlink/": {"GET", "POST"},
    "/api/0/{var}/{issue_id}/plugins/bitbucket/autocomplete": {"GET", "POST"},
    "/api/0/{var}/{issue_id}/plugins/github/create/": {"GET", "POST"},
    "/api/0/{var}/{issue_id}/plugins/github/link/": {"GET", "POST"},
    "/api/0/{var}/{issue_id}/plugins/github/unlink/": {"GET", "POST"},
    "/api/0/{var}/{issue_id}/plugins/github/autocomplete": {"GET", "POST"},
    "/api/0/{var}/{issue_id}/plugins/gitlab/create/": {"GET", "POST"},
    "/api/0/{var}/{issue_id}/plugins/gitlab/link/": {"GET", "POST"},
    "/api/0/{var}/{issue_id}/plugins/gitlab/unlink/": {"GET", "POST"},
    "/api/0/{var}/{issue_id}/plugins/jira/create/": {"GET", "POST"},
    "/api/0/{var}/{issue_id}/plugins/jira/link/": {"GET", "POST"},
    "/api/0/{var}/{issue_id}/plugins/jira/unlink/": {"GET", "POST"},
    "/api/0/{var}/{issue_id}/plugins/jira/autocomplete": {"GET", "POST"},
    "/api/0/{var}/{issue_id}/plugins/pivotal/create/": {"GET", "POST"},
    "/api/0/{var}/{issue_id}/plugins/pivotal/link/": {"GET", "POST"},
    "/api/0/{var}/{issue_id}/plugins/pivotal/unlink/": {"GET", "POST"},
    "/api/0/{var}/{issue_id}/plugins/pivotal/autocomplete": {"GET", "POST"},
    "/api/0/{var}/{issue_id}/plugins/trello/create/": {"GET", "POST"},
    "/api/0/{var}/{issue_id}/plugins/trello/link/": {"GET", "POST"},
    "/api/0/{var}/{issue_id}/plugins/trello/unlink/": {"GET", "POST"},
    "/api/0/{var}/{issue_id}/plugins/trello/options": {"GET", "POST"},
    "/api/0/{var}/{issue_id}/plugins/trello/autocomplete": {"GET", "POST"},
    "/api/0/organizations/": {"GET", "POST"},
    "/api/0/organizations/{organization_id_or_slug}/": {"DELETE", "GET", "PUT"},
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/": {
        "DELETE",
        "GET",
        "PUT",
    },
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/activities/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/events/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/events/{event_id}/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/{var}/": {"GET", "POST"},
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/{var}/{note_id}/": {
        "DELETE",
        "PUT",
    },
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/hashes/": {
        "GET",
        "PUT",
    },
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/reprocessing/": {"POST"},
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/stats/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/tags/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/tags/{key}/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/tags/{key}/values/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/attachments/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/similar/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/external-issues/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/external-issues/{external_issue_id}/": {
        "DELETE"
    },
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/integrations/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/integrations/{integration_id}/": {
        "DELETE",
        "GET",
        "PUT",
        "POST",
    },
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/current-release/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/first-last-release/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/plugins/asana/create/": {
        "GET",
        "POST",
    },
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/plugins/asana/link/": {
        "GET",
        "POST",
    },
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/plugins/asana/unlink/": {
        "GET",
        "POST",
    },
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/plugins/asana/autocomplete": {
        "GET",
        "POST",
    },
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/plugins/bitbucket/create/": {
        "GET",
        "POST",
    },
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/plugins/bitbucket/link/": {
        "GET",
        "POST",
    },
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/plugins/bitbucket/unlink/": {
        "GET",
        "POST",
    },
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/plugins/bitbucket/autocomplete": {
        "GET",
        "POST",
    },
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/plugins/github/create/": {
        "GET",
        "POST",
    },
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/plugins/github/link/": {
        "GET",
        "POST",
    },
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/plugins/github/unlink/": {
        "GET",
        "POST",
    },
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/plugins/github/autocomplete": {
        "GET",
        "POST",
    },
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/plugins/gitlab/create/": {
        "GET",
        "POST",
    },
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/plugins/gitlab/link/": {
        "GET",
        "POST",
    },
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/plugins/gitlab/unlink/": {
        "GET",
        "POST",
    },
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/plugins/jira/create/": {
        "GET",
        "POST",
    },
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/plugins/jira/link/": {
        "GET",
        "POST",
    },
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/plugins/jira/unlink/": {
        "GET",
        "POST",
    },
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/plugins/jira/autocomplete": {
        "GET",
        "POST",
    },
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/plugins/pivotal/create/": {
        "GET",
        "POST",
    },
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/plugins/pivotal/link/": {
        "GET",
        "POST",
    },
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/plugins/pivotal/unlink/": {
        "GET",
        "POST",
    },
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/plugins/pivotal/autocomplete": {
        "GET",
        "POST",
    },
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/plugins/trello/create/": {
        "GET",
        "POST",
    },
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/plugins/trello/link/": {
        "GET",
        "POST",
    },
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/plugins/trello/unlink/": {
        "GET",
        "POST",
    },
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/plugins/trello/options": {
        "GET",
        "POST",
    },
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/plugins/trello/autocomplete": {
        "GET",
        "POST",
    },
    "/api/0/organizations/{organization_id_or_slug}/alert-rules/available-actions/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/alert-rules/{alert_rule_id}/": {
        "DELETE",
        "GET",
        "PUT",
    },
    "/api/0/organizations/{organization_id_or_slug}/alert-rules/": {"GET", "POST"},
    "/api/0/organizations/{organization_id_or_slug}/combined-rules/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/data-export/": {"POST"},
    "/api/0/organizations/{organization_id_or_slug}/data-export/{data_export_id}/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/incidents/{incident_identifier}/activity/": {
        "GET"
    },
    "/api/0/organizations/{organization_id_or_slug}/incidents/{incident_identifier}/comments/": {
        "POST"
    },
    "/api/0/organizations/{organization_id_or_slug}/incidents/{incident_identifier}/comments/{activity_id}/": {
        "DELETE",
        "PUT",
    },
    "/api/0/organizations/{organization_id_or_slug}/incidents/{incident_identifier}/": {
        "GET",
        "PUT",
    },
    "/api/0/organizations/{organization_id_or_slug}/incidents/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/incidents/{incident_identifier}/seen/": {
        "POST"
    },
    "/api/0/organizations/{organization_id_or_slug}/incidents/{incident_identifier}/subscriptions/": {
        "DELETE",
        "POST",
    },
    "/api/0/organizations/{organization_id_or_slug}/chunk-upload/": {"GET", "POST"},
    "/api/0/organizations/{organization_id_or_slug}/code-mappings/": {"GET", "POST"},
    "/api/0/organizations/{organization_id_or_slug}/derive-code-mappings/": {"GET", "POST"},
    "/api/0/organizations/{organization_id_or_slug}/code-mappings/{config_id}/": {
        "DELETE",
        "PUT",
    },
    "/api/0/organizations/{organization_id_or_slug}/code-mappings/{config_id}/codeowners/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/codeowners-associations/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/discover/homepage/": {
        "DELETE",
        "GET",
        "PUT",
    },
    "/api/0/organizations/{organization_id_or_slug}/discover/saved/": {"GET", "POST"},
    "/api/0/organizations/{organization_id_or_slug}/discover/saved/{query_id}/": {
        "DELETE",
        "GET",
        "PUT",
    },
    "/api/0/organizations/{organization_id_or_slug}/discover/saved/{query_id}/visit/": {"POST"},
    "/api/0/organizations/{organization_id_or_slug}/key-transactions/": {
        "DELETE",
        "GET",
        "POST",
    },
    "/api/0/organizations/{organization_id_or_slug}/key-transactions-list/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/related-issues/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/project-transaction-threshold-override/": {
        "DELETE",
        "GET",
        "POST",
    },
    "/api/0/organizations/{organization_id_or_slug}/dashboards/": {"GET", "POST"},
    "/api/0/organizations/{organization_id_or_slug}/dashboards/widgets/": {"POST"},
    "/api/0/organizations/{organization_id_or_slug}/dashboards/{dashboard_id}/": {
        "DELETE",
        "GET",
        "PUT",
    },
    "/api/0/organizations/{organization_id_or_slug}/dashboards/{dashboard_id}/visit/": {"POST"},
    "/api/0/organizations/{organization_id_or_slug}/eventids/{event_id}/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/data-scrubbing-selector-suggestions/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/access-requests/": {"GET", "PUT"},
    "/api/0/organizations/{organization_id_or_slug}/access-requests/{request_id}/": {
        "GET",
        "PUT",
    },
    "/api/0/organizations/{organization_id_or_slug}/activity/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/api-keys/": {"GET", "POST"},
    "/api/0/organizations/{organization_id_or_slug}/api-keys/{api_key_id}/": {
        "DELETE",
        "GET",
        "PUT",
    },
    "/api/0/organizations/{organization_id_or_slug}/audit-logs/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/auth-provider/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/auth-providers/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/avatar/": {"GET", "PUT"},
    "/api/0/organizations/{organization_id_or_slug}/artifactbundle/assemble/": {"POST"},
    "/api/0/organizations/{organization_id_or_slug}/config/integrations/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/config/repos/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/sdk-updates/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/sdks/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/events/{project_id_or_slug}:{event_id}/": {
        "GET"
    },
    "/api/0/organizations/{organization_id_or_slug}/events-stats/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/metrics-estimation-stats/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/events-facets/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/events-facets-stats/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/events-starfish/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/events-facets-performance/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/events-facets-performance-histogram/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/events-span-ops/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/events-spans/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/events-spans-performance/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/events-spans-stats/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/events-root-cause-analysis/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/events-meta/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/spans-samples/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/metrics-compatibility/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/metrics-compatibility-sums/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/missing-members/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/events-histogram/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/events-spans-histogram/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/events-trends/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/events-vitals/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/events-has-measurements/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/events-trends-stats/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/events-trends-statsv2/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/events-trace-light/{trace_id}/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/events-trace/{trace_id}/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/events-trace-meta/{trace_id}/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/measurements-meta/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/issues/": {"DELETE", "GET", "PUT"},
    "/api/0/organizations/{organization_id_or_slug}/issues-count/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/issues-stats/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/integrations/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/integrations/{integration_id}/": {
        "DELETE",
        "GET",
        "POST",
    },
    "/api/0/organizations/{organization_id_or_slug}/integrations/{integration_id}/repos/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/integrations/{integration_id}/issues/": {"PUT"},
    "/api/0/organizations/{organization_id_or_slug}/integrations/{integration_id}/migrate-opsgenie/": {
        "PUT"
    },
    "/api/0/organizations/{organization_id_or_slug}/integrations/{integration_id}/serverless-functions/": {
        "GET",
        "POST",
    },
    "/api/0/organizations/{organization_id_or_slug}/members/": {"GET", "POST"},
    "/api/0/organizations/{organization_id_or_slug}/external-users/": {"POST"},
    "/api/0/organizations/{organization_id_or_slug}/external-users/{external_user_id}/": {
        "DELETE",
        "PUT",
    },
    "/api/0/organizations/{organization_id_or_slug}/integration-requests/": {"POST"},
    "/api/0/organizations/{organization_id_or_slug}/invite-requests/": {"GET", "POST"},
    "/api/0/organizations/{organization_id_or_slug}/invite-requests/{member_id}/": {
        "DELETE",
        "GET",
        "PUT",
    },
    "/api/0/organizations/{organization_id_or_slug}/notifications/actions/": {"GET", "POST"},
    "/api/0/organizations/{organization_id_or_slug}/notifications/actions/{action_id}/": {
        "DELETE",
        "GET",
        "PUT",
    },
    "/api/0/organizations/{organization_id_or_slug}/notifications/available-actions/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/monitors-stats/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/monitors/{monitor_id_or_slug}/stats/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/pinned-searches/": {"DELETE", "PUT"},
    "/api/0/organizations/{organization_id_or_slug}/recent-searches/": {"GET", "POST"},
    "/api/0/organizations/{organization_id_or_slug}/searches/{search_id}/": {"DELETE", "PUT"},
    "/api/0/organizations/{organization_id_or_slug}/searches/": {"GET", "POST"},
    "/api/0/organizations/{organization_id_or_slug}/sessions/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/releases/{version}/resolved/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/request-project-creation/": {"POST"},
    "/api/0/organizations/{organization_id_or_slug}/members/{member_id}/teams/{team_id_or_slug}/": {
        "GET",
        "PUT",
    },
    "/api/0/organizations/{organization_id_or_slug}/onboarding-continuation-email/": {"POST"},
    "/api/0/organizations/{organization_id_or_slug}/processingissues/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/experimental/projects/": {"POST"},
    "/api/0/organizations/{organization_id_or_slug}/projects-count/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/sent-first-event/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/repos/": {"GET", "POST"},
    "/api/0/organizations/{organization_id_or_slug}/repos/{repo_id}/": {"DELETE", "PUT"},
    "/api/0/organizations/{organization_id_or_slug}/repos/{repo_id}/commits/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/plugins/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/plugins/configs/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/releases/": {"GET", "POST"},
    "/api/0/organizations/{organization_id_or_slug}/releases/stats/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/releases/{version}/": {
        "DELETE",
        "GET",
        "PUT",
    },
    "/api/0/organizations/{organization_id_or_slug}/releases/{version}/meta/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/releases/{version}/assemble/": {"POST"},
    "/api/0/organizations/{organization_id_or_slug}/releases/{version}/files/": {"GET", "POST"},
    "/api/0/organizations/{organization_id_or_slug}/releases/{version}/files/{file_id}/": {
        "DELETE",
        "GET",
        "PUT",
    },
    "/api/0/organizations/{organization_id_or_slug}/releases/{version}/commitfiles/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/releases/{version}/deploys/": {
        "GET",
        "POST",
    },
    "/api/0/organizations/{organization_id_or_slug}/releases/{version}/commits/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/releases/{version}/previous-with-commits/": {
        "GET"
    },
    "/api/0/organizations/{organization_id_or_slug}/user-feedback/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/user-teams/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/users/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/users/{user_id}/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/sentry-app-installations/": {"GET", "POST"},
    "/api/0/organizations/{organization_id_or_slug}/sentry-apps/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/sentry-app-components/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/org-auth-tokens/": {"GET", "POST"},
    "/api/0/organizations/{organization_id_or_slug}/org-auth-tokens/{token_id}/": {
        "DELETE",
        "GET",
        "PUT",
    },
    "/api/0/organizations/{organization_id_or_slug}/stats/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/tags/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/tags/{key}/values/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/onboarding-tasks/": {"POST"},
    "/api/0/organizations/{organization_id_or_slug}/environments/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/broadcasts/": {"GET", "PUT", "POST"},
    "/api/0/organizations/{organization_id_or_slug}/join-request/": {"POST"},
    "/api/0/organizations/{organization_id_or_slug}/transaction-anomaly-detection/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/relay_usage/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/replay-selectors/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/replay-count/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/replays-events-meta/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/functions/": {"GET", "POST"},
    "/api/0/organizations/{organization_id_or_slug}/functions/{function_id_or_slug}/": {
        "DELETE",
        "GET",
        "PUT",
    },
    "/api/0/organizations/{organization_id_or_slug}/scim/v2/Users/{member_id}": {"PUT"},
    "/api/0/organizations/{organization_id_or_slug}/scim/v2/Groups/{team_id}": {"PUT"},
    "/api/0/organizations/{organization_id_or_slug}/scim/v2/Schemas": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/metrics/data/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/profiling/filters/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/profiling/flamegraph/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/profiling/function-trends/": {"GET"},
    "/api/0/projects/": {"GET"},
    "/api/0/projects/{organization_id_or_slug}/rule-conditions/": {"GET"},
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/alert-rules/{alert_rule_id}/": {
        "DELETE",
        "GET",
        "PUT",
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/alert-rules/": {
        "GET",
        "POST",
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/alert-rule-task/{task_uuid}/": {
        "GET"
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/combined-rules/": {"GET"},
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/avatar/": {"GET", "PUT"},
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/create-sample/": {"POST"},
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/create-sample-transaction/": {
        "POST"
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/docs/{platform}/": {"GET"},
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/environments/": {"GET"},
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/environments/{environment}/": {
        "GET",
        "PUT",
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/platforms/": {"GET"},
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/events/": {"GET"},
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/events/{event_id}/": {"GET"},
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/events/{event_id}/grouping-info/": {
        "GET"
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/events/{event_id}/apple-crash-report": {
        "GET"
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/events/{event_id}/attachments/": {
        "GET"
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/events/{event_id}/reprocessable/": {
        "GET"
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/events/{event_id}/attachments/{attachment_id}/": {
        "GET",
        "DELETE",
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/events/{event_id}/committers/": {
        "GET"
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/events/{event_id}/json/": {
        "GET"
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/events/{event_id}/owners/": {
        "GET"
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/events/{event_id}/actionable-items/": {
        "GET"
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/files/dsyms/": {
        "DELETE",
        "GET",
        "POST",
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/files/source-maps/": {
        "GET",
        "DELETE",
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/files/artifact-bundles/": {
        "GET",
        "DELETE",
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/files/proguard-artifact-releases": {
        "GET",
        "POST",
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/files/difs/assemble/": {"POST"},
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/files/dsyms/unknown/": {"GET"},
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/files/dsyms/associate/": {
        "POST"
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/filters/": {"GET"},
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/hooks/": {"GET", "POST"},
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/hooks/{hook_id}/": {
        "DELETE",
        "GET",
        "PUT",
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/hooks/{hook_id}/stats/": {
        "GET"
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/{var}/": {
        "POST",
        "DELETE",
        "GET",
        "PUT",
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/{var}/stats/": {"GET"},
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/keys/{key_id}/stats/": {"GET"},
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/members/": {"GET"},
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/releases/": {"GET", "POST"},
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/commits/": {"GET"},
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/releases/token/": {
        "GET",
        "POST",
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/releases/completion/": {"GET"},
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/releases/{version}/": {
        "DELETE",
        "GET",
        "PUT",
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/releases/{version}/commits/": {
        "GET"
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/releases/{version}/repositories/": {
        "GET"
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/releases/{version}/resolved/": {
        "GET"
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/releases/{version}/stats/": {
        "GET"
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/artifact-bundles/{bundle_id}/files/": {
        "GET"
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/artifact-bundles/{bundle_id}/files/{file_id}/": {
        "GET"
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/releases/{version}/files/": {
        "GET",
        "POST",
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/releases/{version}/files/{file_id}/": {
        "DELETE",
        "GET",
        "PUT",
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/artifact-lookup/": {"GET"},
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/rules/": {"GET", "POST"},
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/replays/{replay_id}/": {
        "GET",
        "DELETE",
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/replays/{replay_id}/clicks/": {
        "GET"
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/replays/{replay_id}/recording-segments/": {
        "GET"
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/replays/{replay_id}/recording-segments/{segment_id}/": {
        "GET"
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/rules/configuration/": {"GET"},
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/rules/{rule_id}/": {
        "DELETE",
        "GET",
        "PUT",
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/rules/{rule_id}/enable/": {
        "PUT"
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/rules/{rule_id}/snooze/": {
        "DELETE",
        "POST",
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/alert-rules/{rule_id}/snooze/": {
        "DELETE",
        "POST",
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/rules/preview/": {"POST"},
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/rule-actions/": {"POST"},
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/rules/{rule_id}/group-history/": {
        "GET"
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/rules/{rule_id}/stats/": {
        "GET"
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/rule-task/{task_uuid}/": {
        "GET"
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/stats/": {"GET"},
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/tags/": {"GET"},
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/tags/{key}/": {
        "GET",
        "DELETE",
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/tags/{key}/values/": {"GET"},
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/teams/": {"GET"},
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/transfer/": {"POST"},
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/users/": {"GET"},
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/users/{user_hash}/": {
        "GET",
        "DELETE",
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/user-stats/": {"GET"},
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/processingissues/": {
        "GET",
        "DELETE",
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/reprocessing/": {"POST"},
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/processingissues/discard/": {
        "DELETE"
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/ownership/": {"GET", "PUT"},
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/codeowners/": {
        "GET",
        "POST",
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/codeowners/{codeowners_id}/": {
        "DELETE",
        "PUT",
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/transaction-threshold/configure/": {
        "DELETE",
        "GET",
        "POST",
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/performance-issues/configure/": {
        "DELETE",
        "GET",
        "PUT",
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/plugins/": {"GET"},
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/plugins/{plugin_id}/": {
        "DELETE",
        "GET",
        "PUT",
        "POST",
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/cluster-transaction-names/": {
        "GET"
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/tombstones/": {"GET"},
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/tombstones/{tombstone_id}/": {
        "DELETE"
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/stacktrace-link/": {"GET"},
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/grouping-configs/": {"GET"},
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/appstoreconnect/": {"POST"},
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/appstoreconnect/apps/": {
        "POST"
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/appstoreconnect/status/": {
        "GET"
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/appstoreconnect/{credentials_id}/": {
        "POST"
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/appstoreconnect/{credentials_id}/refresh/": {
        "POST"
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/profiling/functions/": {"GET"},
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/profiling/profiles/{profile_id}/": {
        "GET"
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/profiling/raw_profiles/{profile_id}/": {
        "GET"
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/profiling/flamegraph/": {"GET"},
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/profiling/transactions/{transaction_id}/": {
        "GET"
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/dynamic-sampling/rate/": {
        "GET"
    },
    "/api/0/projects/{organization_id_or_slug}/{project_id_or_slug}/repo-path-parsing/": {"POST"},
    "/api/0/teams/{organization_id_or_slug}/{team_id_or_slug}/": {"DELETE", "GET", "PUT"},
    "/api/0/teams/{organization_id_or_slug}/{team_id_or_slug}/issues/old/": {"GET"},
    "/api/0/teams/{organization_id_or_slug}/{team_id_or_slug}/release-count/": {"GET"},
    "/api/0/teams/{organization_id_or_slug}/{team_id_or_slug}/time-to-resolution/": {"GET"},
    "/api/0/teams/{organization_id_or_slug}/{team_id_or_slug}/unresolved-issue-age/": {"GET"},
    "/api/0/teams/{organization_id_or_slug}/{team_id_or_slug}/alerts-triggered/": {"GET"},
    "/api/0/teams/{organization_id_or_slug}/{team_id_or_slug}/alerts-triggered-index/": {"GET"},
    "/api/0/teams/{organization_id_or_slug}/{team_id_or_slug}/issue-breakdown/": {"GET"},
    "/api/0/teams/{organization_id_or_slug}/{team_id_or_slug}/all-unresolved-issues/": {"GET"},
    "/api/0/teams/{organization_id_or_slug}/{team_id_or_slug}/notification-settings/": {
        "GET",
        "PUT",
    },
    "/api/0/teams/{organization_id_or_slug}/{team_id_or_slug}/members/": {"GET"},
    "/api/0/teams/{organization_id_or_slug}/{team_id_or_slug}/stats/": {"GET"},
    "/api/0/teams/{organization_id_or_slug}/{team_id_or_slug}/avatar/": {"GET", "PUT"},
    "/api/0/teams/{organization_id_or_slug}/{team_id_or_slug}/external-teams/": {"POST"},
    "/api/0/teams/{organization_id_or_slug}/{team_id_or_slug}/external-teams/{external_team_id}/": {
        "DELETE",
        "PUT",
    },
    "/api/0/users/": {"GET"},
    "/api/0/users/{user_id}/": {"DELETE", "GET", "PUT"},
    "/api/0/users/{user_id}/avatar/": {"GET", "PUT"},
    "/api/0/users/{user_id}/authenticators/": {"GET"},
    "/api/0/users/{user_id}/authenticators/{interface_id}/enroll/": {"GET", "POST"},
    "/api/0/users/{user_id}/authenticators/{auth_id}/{interface_device_id}/": {
        "DELETE",
        "GET",
        "PUT",
    },
    "/api/0/users/{user_id}/authenticators/{auth_id}/": {"DELETE", "GET", "PUT"},
    "/api/0/users/{user_id}/emails/": {"DELETE", "GET", "PUT", "POST"},
    "/api/0/users/{user_id}/emails/confirm/": {"POST"},
    "/api/0/users/{user_id}/identities/{identity_id}/": {"DELETE"},
    "/api/0/users/{user_id}/identities/": {"GET"},
    "/api/0/users/{user_id}/ips/": {"GET"},
    "/api/0/users/{user_id}/organizations/": {"GET"},
    "/api/0/users/{user_id}/notification-settings/": {"GET", "PUT"},
    "/api/0/users/{user_id}/notifications/": {"GET", "PUT"},
    "/api/0/users/{user_id}/notifications/{notification_type}/": {"GET", "PUT"},
    "/api/0/users/{user_id}/password/": {"PUT"},
    "/api/0/users/{user_id}/permissions/": {"GET"},
    "/api/0/users/{user_id}/permissions/config/": {"GET"},
    "/api/0/users/{user_id}/permissions/{permission_name}/": {"DELETE", "GET", "POST"},
    "/api/0/users/{user_id}/roles/": {"GET"},
    "/api/0/users/{user_id}/roles/{role_name}/": {"DELETE", "GET", "POST"},
    "/api/0/users/{user_id}/subscriptions/": {"GET", "PUT", "POST"},
    "/api/0/users/{user_id}/organization-integrations/": {"GET"},
    "/api/0/users/{user_id}/user-identities/": {"GET"},
    "/api/0/users/{user_id}/user-identities/{category}/{identity_id}/": {"GET", "DELETE"},
    "/api/0/userroles/": {"GET", "POST"},
    "/api/0/userroles/{role_name}/": {"DELETE", "GET", "PUT"},
    "/api/0/sentry-apps/": {"GET", "POST"},
    "/api/0/sentry-apps/{sentry_app_id_or_slug}/": {"DELETE", "GET", "PUT"},
    "/api/0/sentry-apps/{sentry_app_id_or_slug}/features/": {"GET"},
    "/api/0/sentry-apps/{sentry_app_id_or_slug}/components/": {"GET"},
    "/api/0/sentry-apps/{sentry_app_id_or_slug}/avatar/": {"GET", "PUT"},
    "/api/0/sentry-apps/{sentry_app_id_or_slug}/api-tokens/": {"GET", "POST"},
    "/api/0/sentry-apps/{sentry_app_id_or_slug}/api-tokens/{api_token}/": {"DELETE"},
    "/api/0/sentry-apps/{sentry_app_id_or_slug}/stats/": {"GET"},
    "/api/0/sentry-apps/{sentry_app_id_or_slug}/requests/": {"GET"},
    "/api/0/sentry-apps/{sentry_app_id_or_slug}/interaction/": {"GET", "POST"},
    "/api/0/sentry-apps/{sentry_app_id_or_slug}/publish-request/": {"POST"},
    "/api/0/sentry-app-installations/{uuid}/": {"DELETE", "GET", "PUT"},
    "/api/0/sentry-app-installations/{uuid}/authorizations/": {"POST"},
    "/api/0/sentry-app-installations/{uuid}/external-requests/": {"GET"},
    "/api/0/sentry-app-installations/{uuid}/external-issue-actions/": {"POST"},
    "/api/0/sentry-app-installations/{uuid}/external-issues/": {"POST"},
    "/api/0/sentry-app-installations/{uuid}/external-issues/{external_issue_id}/": {"DELETE"},
    "/api/0/auth/": {"DELETE", "GET", "PUT", "POST"},
    "/api/0/auth/config/": {"GET"},
    "/api/0/auth/login/": {"POST"},
    "/api/0/broadcasts/": {"GET", "PUT", "POST"},
    "/api/0/broadcasts/{broadcast_id}/": {"GET", "PUT"},
    "/api/0/assistant/": {"GET", "PUT"},
    "/api/0/api-applications/": {"GET", "POST"},
    "/api/0/api-applications/{app_id}/": {"DELETE", "GET", "PUT"},
    "/api/0/api-applications/{app_id}/rotate-secret/": {"POST"},
    "/api/0/api-authorizations/": {"GET", "DELETE"},
    "/api/0/api-tokens/": {"DELETE", "GET", "POST"},
    "/api/0/prompts-activity/": {"GET", "PUT"},
    "/api/0/organizations/{organization_id_or_slug}/prompts-activity/": {"GET", "PUT"},
    "/api/0/authenticators/": {"GET"},
    "/api/0/accept-transfer/": {"GET", "POST"},
    "/api/0/accept-invite/{organization_id_or_slug}/{member_id}/{token}/": {"GET", "POST"},
    "/api/0/accept-invite/{member_id}/{token}/": {"GET", "POST"},
    "/api/0/profiling/projects/{project_id}/profile/{profile_id}/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/{var}/{issue_id}/participants/": {"GET"},
    "/api/0/{var}/{issue_id}/participants/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/shared/{var}/{share_id}/": {"GET"},
    "/api/0/shared/{var}/{share_id}/": {"GET"},
    "/api/0/sentry-apps-stats/": {"GET"},
    "/api/0/doc-integrations/": {"GET", "POST"},
    "/api/0/doc-integrations/{doc_integration_id_or_slug}/": {"DELETE", "GET", "PUT"},
    "/api/0/doc-integrations/{doc_integration_id_or_slug}/avatar/": {"GET", "PUT"},
    "/api/0/integration-features/": {"GET"},
    "/api/0/issue-occurrence/": {"POST"},
    "/api/0/grouping-configs/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/grouping-configs/": {"GET"},
    "/api/0/builtin-symbol-sources/": {"GET"},
    "/api/0/organizations/{organization_id_or_slug}/builtin-symbol-sources/": {"GET"},
    "/api/0/wizard/": {"GET", "DELETE"},
    "/api/0/wizard/{wizard_hash}/": {"GET", "DELETE"},
    "/api/0/internal/health/": {"GET"},
    "/api/0/internal/options/": {"GET", "PUT"},
    "/api/0/internal/beacon/": {"POST"},
    "/api/0/internal/quotas/": {"GET"},
    "/api/0/internal/queue/tasks/": {"GET"},
    "/api/0/internal/stats/": {"GET"},
    "/api/0/internal/warnings/": {"GET"},
    "/api/0/internal/packages/": {"GET"},
    "/api/0/internal/environment/": {"GET"},
    "/api/0/internal/mail/": {"GET", "POST"},
    "/api/0/internal/project-config/": {"GET"},
    "/api/0/internal/rpc/{service_name}/{method_name}/": {"POST"},
    "/api/0/internal/check-am2-compatibility/": {"GET"},
    "/api/0/": {"GET"},
    "/oauth/userinfo/": {"GET"},
    "/extensions/jira/descriptor/": {"GET"},
    "/extensions/jira/installed/": {"POST"},
    "/extensions/jira/uninstalled/": {"POST"},
    "/extensions/jira/issue-updated/": {"POST"},
    "/extensions/jira/search/{organization_id_or_slug}/{integration_id}/": {"GET"},
    "/extensions/jira-server/issue-updated/{token}/": {"POST"},
    "/extensions/jira-server/search/{organization_id_or_slug}/{integration_id}/": {"GET"},
    "/extensions/slack/action/": {"POST"},
    "/extensions/slack/commands/": {"POST"},
    "/extensions/slack/event/": {"POST"},
    "/extensions/github/webhook/": {"POST"},
    "/extensions/github/search/{organization_id_or_slug}/{integration_id}/": {"GET"},
    "/extensions/github-enterprise/webhook/": {"POST"},
    "/extensions/gitlab/search/{organization_id_or_slug}/{integration_id}/": {"GET"},
    "/extensions/gitlab/webhook/": {"POST"},
    "/extensions/vsts/issue-updated/": {"POST"},
    "/extensions/vsts/search/{organization_id_or_slug}/{integration_id}/": {"GET"},
    "/extensions/bitbucket/descriptor/": {"GET"},
    "/extensions/bitbucket/installed/": {"POST"},
    "/extensions/bitbucket/uninstalled/": {"POST"},
    "/extensions/bitbucket/organizations/{organization_id}/webhook/": {"POST"},
    "/extensions/bitbucket/search/{organization_id_or_slug}/{integration_id}/": {"GET"},
    "/extensions/vercel/delete/": {"DELETE", "POST"},
    "/extensions/vercel/webhook/": {"DELETE", "POST"},
    "/extensions/msteams/webhook/": {"POST"},
    "/extensions/discord/interactions/": {"POST"},
}
