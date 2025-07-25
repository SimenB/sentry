from collections.abc import Sequence
from typing import TypedDict

from django.db.models.query import QuerySet

from sentry.models.promptsactivity import PromptsActivity


class _PromptConfig(TypedDict):
    required_fields: list[str]


DEFAULT_PROMPTS: dict[str, _PromptConfig] = {
    "alert_stream": {"required_fields": ["organization_id"]},
    "chonk_ui_dot_indicator": {"required_fields": ["organization_id"]},
    "chonk_ui_banner": {"required_fields": ["organization_id"]},
    "code_owners": {"required_fields": ["organization_id", "project_id"]},
    "data_consent_banner": {"required_fields": ["organization_id"]},
    "data_consent_priority": {"required_fields": ["organization_id"]},
    "distributed_tracing": {"required_fields": ["organization_id", "project_id"]},
    "github_missing_members": {"required_fields": ["organization_id"]},
    "issue_feature_flags_inline_onboarding": {"required_fields": ["organization_id", "project_id"]},
    "issue_feedback_hidden": {"required_fields": ["organization_id", "project_id"]},
    "issue_priority": {"required_fields": ["organization_id"]},
    "issue_replay_inline_onboarding": {"required_fields": ["organization_id", "project_id"]},
    "issue_views_add_view_banner": {"required_fields": ["organization_id"]},
    "issue_views_all_views_banner": {"required_fields": ["organization_id"]},
    "metric_alert_ignore_archived_issues": {"required_fields": ["organization_id", "project_id"]},
    "profiling_onboarding": {"required_fields": ["organization_id"]},
    "quick_trace_missing": {"required_fields": ["organization_id", "project_id"]},
    "releases": {"required_fields": ["organization_id", "project_id"]},
    "sdk_updates": {"required_fields": ["organization_id"]},
    "seer_autofix_setup_acknowledged": {"required_fields": ["organization_id"]},
    "stacked_navigation_banner": {"required_fields": ["organization_id"]},
    "stacked_navigation_help_menu": {"required_fields": ["organization_id"]},
    "stacktrace_link": {"required_fields": ["organization_id", "project_id"]},
    "suggest_mobile_project": {"required_fields": ["organization_id"]},
    "suspect_commits": {"required_fields": ["organization_id", "project_id"]},
    "vitals_alert": {"required_fields": ["organization_id"]},
}


class PromptsConfig:
    """
    Used to configure available 'prompts' (frontend modals or UI that may be
    dismissed or have some other action recorded about it). This config
    declares what prompts are available And what fields may be required.

    required_fields available: [organization_id, project_id]
    """

    def __init__(self, prompts: dict[str, _PromptConfig]):
        self.prompts = prompts

    def add(self, name: str, config: _PromptConfig) -> None:
        if self.has(name):
            raise Exception(f"Prompt key {name} is already in use")
        if "required_fields" not in config:
            raise Exception("'required_fields' must be present in the config dict")

        self.prompts[name] = config

    def has(self, name: str) -> bool:
        return name in self.prompts

    def get(self, name: str) -> _PromptConfig:
        return self.prompts[name]

    def required_fields(self, name: str) -> list[str]:
        return self.prompts[name]["required_fields"]


prompt_config = PromptsConfig(DEFAULT_PROMPTS)


def get_prompt_activities_for_user(
    organization_ids: Sequence[int], user_id: int, features: Sequence[str]
) -> QuerySet[PromptsActivity]:
    return PromptsActivity.objects.filter(
        organization_id__in=organization_ids, feature__in=features, user_id=user_id
    )
