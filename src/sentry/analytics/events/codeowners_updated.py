from sentry import analytics


@analytics.eventclass("codeowners.updated")
class CodeOwnersUpdated(analytics.Event):
    user_id: int | None = None
    organization_id: int
    project_id: int
    codeowners_id: int


analytics.register(CodeOwnersUpdated)
