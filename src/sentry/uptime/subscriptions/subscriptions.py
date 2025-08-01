import logging
from collections.abc import Sequence

from django.db import router

from sentry import quotas
from sentry.constants import DataCategory, ObjectStatus
from sentry.deletions.models.scheduleddeletion import RegionScheduledDeletion
from sentry.models.environment import Environment
from sentry.models.project import Project
from sentry.quotas.base import SeatAssignmentResult
from sentry.types.actor import Actor
from sentry.uptime.detectors.url_extraction import extract_domain_parts
from sentry.uptime.grouptype import UptimeDomainCheckFailure
from sentry.uptime.issue_platform import resolve_uptime_issue
from sentry.uptime.models import (
    ProjectUptimeSubscription,
    UptimeStatus,
    UptimeSubscription,
    UptimeSubscriptionRegion,
    create_detector_from_project_subscription,
    get_detector,
    get_project_subscription,
    load_regions_for_uptime_subscription,
)
from sentry.uptime.rdap.tasks import fetch_subscription_rdap_info
from sentry.uptime.subscriptions.regions import UptimeRegionWithMode, get_active_regions
from sentry.uptime.subscriptions.tasks import (
    create_remote_uptime_subscription,
    delete_remote_uptime_subscription,
    send_uptime_config_deletion,
    update_remote_uptime_subscription,
)
from sentry.uptime.types import UptimeMonitorMode
from sentry.utils.db import atomic_transaction
from sentry.utils.not_set import NOT_SET, NotSet, default_if_not_set
from sentry.utils.outcomes import Outcome
from sentry.workflow_engine.models import DataSource, DataSourceDetector, Detector

logger = logging.getLogger(__name__)

UPTIME_SUBSCRIPTION_TYPE = "uptime_monitor"
MAX_AUTO_SUBSCRIPTIONS_PER_ORG = 1
MAX_MANUAL_SUBSCRIPTIONS_PER_ORG = 100
MAX_MONITORS_PER_DOMAIN = 100


class MaxManualUptimeSubscriptionsReached(ValueError):
    pass


class UptimeMonitorNoSeatAvailable(Exception):
    """
    Indicates that the quotes system is unable to allocate a seat for the new
    uptime monitor.
    """

    result: SeatAssignmentResult | None
    """
    The assignment result. In rare cases may be None when there is a race
    condition and seat assignment is not accepted after passing the assignment
    check.
    """

    def __init__(self, result: SeatAssignmentResult | None) -> None:
        super().__init__()
        self.result = result


def create_uptime_subscription(
    url: str,
    interval_seconds: int,
    timeout_ms: int,
    method: str = "GET",
    headers: Sequence[tuple[str, str]] | None = None,
    body: str | None = None,
    trace_sampling: bool = False,
    uptime_status: UptimeStatus = UptimeStatus.OK,
) -> UptimeSubscription:
    """
    Creates a new uptime subscription. This creates the row in postgres, and fires a task that will send the config
    to the uptime check system.
    """
    if headers is None:
        headers = []
    # We extract the domain and suffix of the url here. This is used to prevent there being too many checks to a single
    # domain.
    result = extract_domain_parts(url)

    subscription = UptimeSubscription.objects.create(
        url=url,
        url_domain=result.domain,
        url_domain_suffix=result.suffix,
        interval_seconds=interval_seconds,
        timeout_ms=timeout_ms,
        status=UptimeSubscription.Status.CREATING.value,
        type=UPTIME_SUBSCRIPTION_TYPE,
        method=method,
        headers=headers,  # type: ignore[misc]
        body=body,
        trace_sampling=trace_sampling,
        uptime_status=uptime_status,
    )

    # Associate active regions with this subscription
    for region_config in get_active_regions():
        UptimeSubscriptionRegion.objects.create(
            uptime_subscription=subscription,
            region_slug=region_config.slug,
            mode=region_config.mode,
        )

    create_remote_uptime_subscription.delay(subscription.id)
    fetch_subscription_rdap_info.delay(subscription.id)
    return subscription


def update_uptime_subscription(
    subscription: UptimeSubscription,
    url: str | NotSet = NOT_SET,
    interval_seconds: int | NotSet = NOT_SET,
    timeout_ms: int | NotSet = NOT_SET,
    method: str | NotSet = NOT_SET,
    headers: Sequence[tuple[str, str]] | None | NotSet = NOT_SET,
    body: str | None | NotSet = NOT_SET,
    trace_sampling: bool | NotSet = NOT_SET,
):
    """
    Updates an existing uptime subscription. This updates the row in postgres, and fires a task that will send the
    config to the uptime check system.
    """
    url = default_if_not_set(subscription.url, url)
    # We extract the domain and suffix of the url here. This is used to prevent there being too many checks to a single
    # domain.
    result = extract_domain_parts(url)
    headers = default_if_not_set(subscription.headers, headers)
    if headers is None:
        headers = []

    subscription.update(
        status=UptimeSubscription.Status.UPDATING.value,
        url=url,
        url_domain=result.domain,
        url_domain_suffix=result.suffix,
        interval_seconds=default_if_not_set(subscription.interval_seconds, interval_seconds),
        timeout_ms=default_if_not_set(subscription.timeout_ms, timeout_ms),
        method=default_if_not_set(subscription.method, method),
        headers=headers,
        body=default_if_not_set(subscription.body, body),
        trace_sampling=default_if_not_set(subscription.trace_sampling, trace_sampling),
    )

    # Associate active regions with this subscription
    check_and_update_regions(subscription, load_regions_for_uptime_subscription(subscription.id))
    update_remote_uptime_subscription.delay(subscription.id)
    fetch_subscription_rdap_info.delay(subscription.id)


def delete_uptime_subscription(uptime_subscription: UptimeSubscription):
    """
    Deletes an existing uptime subscription. This updates the row in postgres, and fires a task that will send the
    deletion to the external system and remove the row once successful.
    """
    uptime_subscription.update(status=UptimeSubscription.Status.DELETING.value)
    delete_remote_uptime_subscription.delay(uptime_subscription.id)


def create_project_uptime_subscription(
    project: Project,
    environment: Environment | None,
    url: str,
    interval_seconds: int,
    timeout_ms: int,
    method: str = "GET",
    headers: Sequence[tuple[str, str]] | None = None,
    body: str | None = None,
    mode: UptimeMonitorMode = UptimeMonitorMode.MANUAL,
    status: int = ObjectStatus.ACTIVE,
    name: str = "",
    owner: Actor | None = None,
    trace_sampling: bool = False,
    override_manual_org_limit: bool = False,
    uptime_status: UptimeStatus = UptimeStatus.OK,
) -> ProjectUptimeSubscription:
    """
    Creates an UptimeSubscription and associated ProjectUptimeSubscription
    """
    if mode == UptimeMonitorMode.MANUAL:
        manual_subscription_count = Detector.objects.filter(
            type=UptimeDomainCheckFailure.slug,
            project__organization=project.organization,
            config__mode=UptimeMonitorMode.MANUAL,
        ).count()

        # Once a user has created a subscription manually, make sure we disable all autodetection, and remove any
        # onboarding monitors
        if project.organization.get_option("sentry:uptime_autodetection", False):
            project.organization.update_option("sentry:uptime_autodetection", False)
            for detector in get_auto_monitored_detectors_for_project(
                project, modes=[UptimeMonitorMode.AUTO_DETECTED_ONBOARDING]
            ):
                delete_uptime_detector(detector)

        if (
            not override_manual_org_limit
            and manual_subscription_count >= MAX_MANUAL_SUBSCRIPTIONS_PER_ORG
        ):
            raise MaxManualUptimeSubscriptionsReached

    with atomic_transaction(
        using=(
            router.db_for_write(UptimeSubscription),
            router.db_for_write(ProjectUptimeSubscription),
            router.db_for_write(DataSource),
            router.db_for_write(Detector),
            router.db_for_write(DataSourceDetector),
        )
    ):
        uptime_subscription = create_uptime_subscription(
            url=url,
            interval_seconds=interval_seconds,
            timeout_ms=timeout_ms,
            method=method,
            headers=headers,
            body=body,
            trace_sampling=trace_sampling,
            uptime_status=uptime_status,
        )
        owner_user_id = None
        owner_team_id = None
        if owner:
            if owner.is_user:
                owner_user_id = owner.id
            if owner.is_team:
                owner_team_id = owner.id
        uptime_monitor = ProjectUptimeSubscription.objects.create(
            project=project,
            environment=environment,
            uptime_subscription=uptime_subscription,
            mode=mode.value,
            name=name,
            owner_user_id=owner_user_id,
            owner_team_id=owner_team_id,
        )
        detector = create_detector_from_project_subscription(uptime_monitor)

        # Don't consume a seat if we're still in onboarding mode
        if mode != UptimeMonitorMode.AUTO_DETECTED_ONBOARDING:
            # Update status. This may have the side effect of removing or creating a
            # remote subscription. When a new monitor is created we will ensure seat
            # assignment, which may cause the monitor to be disabled if there are no
            # available seat assignments.
            match status:
                case ObjectStatus.ACTIVE:
                    try:
                        enable_uptime_detector(detector, ensure_assignment=True)
                    except UptimeMonitorNoSeatAvailable:
                        # No need to do anything if we failed to handle seat
                        # assignment. The monitor will be created, but not enabled
                        pass
                case ObjectStatus.DISABLED:
                    disable_uptime_detector(detector)

    # ProjectUptimeSubscription may have been updated as part of
    # {enable,disable}_uptime_detector
    uptime_monitor.refresh_from_db()

    return uptime_monitor


def update_project_uptime_subscription(
    uptime_monitor: ProjectUptimeSubscription,
    environment: Environment | None | NotSet = NOT_SET,
    url: str | NotSet = NOT_SET,
    interval_seconds: int | NotSet = NOT_SET,
    timeout_ms: int | NotSet = NOT_SET,
    method: str | NotSet = NOT_SET,
    headers: Sequence[tuple[str, str]] | NotSet = NOT_SET,
    body: str | None | NotSet = NOT_SET,
    name: str | NotSet = NOT_SET,
    owner: Actor | None | NotSet = NOT_SET,
    trace_sampling: bool | NotSet = NOT_SET,
    status: int = ObjectStatus.ACTIVE,
    mode: UptimeMonitorMode = UptimeMonitorMode.MANUAL,
    ensure_assignment: bool = False,
):
    """
    Links a project to an uptime subscription so that it can process results.
    """
    with atomic_transaction(
        using=(
            router.db_for_write(UptimeSubscription),
            router.db_for_write(ProjectUptimeSubscription),
            router.db_for_write(Detector),
        )
    ):
        update_uptime_subscription(
            uptime_monitor.uptime_subscription,
            url=url,
            interval_seconds=interval_seconds,
            timeout_ms=timeout_ms,
            method=method,
            headers=headers,
            body=body,
            trace_sampling=trace_sampling,
        )

        owner_user_id = uptime_monitor.owner_user_id
        owner_team_id = uptime_monitor.owner_team_id
        if owner and owner is not NOT_SET:
            if owner.is_user:
                owner_user_id = owner.id
                owner_team_id = None
            if owner.is_team:
                owner_team_id = owner.id
                owner_user_id = None

        env = default_if_not_set(uptime_monitor.environment, environment)
        uptime_monitor.update(
            environment=env,
            name=default_if_not_set(uptime_monitor.name, name),
            mode=mode,
            owner_user_id=owner_user_id,
            owner_team_id=owner_team_id,
        )

        detector = get_detector(uptime_monitor.uptime_subscription)
        assert detector
        detector.update(
            name=default_if_not_set(uptime_monitor.name, name),
            owner_user_id=owner_user_id,
            owner_team_id=owner_team_id,
            config={
                "mode": mode,
                "environment": env.name if env else None,
            },
        )

        # Don't consume a seat if we're still in onboarding mode
        if mode != UptimeMonitorMode.AUTO_DETECTED_ONBOARDING:
            # Update status. This may have the side effect of removing or creating a
            # remote subscription. Will raise a UptimeMonitorNoSeatAvailable if seat
            # assignment fails.
            match status:
                case ObjectStatus.DISABLED:
                    disable_uptime_detector(detector)
                case ObjectStatus.ACTIVE:
                    enable_uptime_detector(detector, ensure_assignment=ensure_assignment)

    # ProjectUptimeSubscription may have been updated as part of
    # {enable,disable}_uptime_detector
    uptime_monitor.refresh_from_db()


def disable_uptime_detector(detector: Detector, skip_quotas: bool = False):
    """
    Disables a uptime detector. The associated ProjectUptimeSubscription will also be disabled,
    and if the UptimeSubscription no longer has any active ProjectUptimeSubscriptions, it will
    also be disabled.
    """
    with atomic_transaction(
        using=(
            router.db_for_write(UptimeSubscription),
            router.db_for_write(ProjectUptimeSubscription),
            router.db_for_write(Detector),
        )
    ):
        uptime_monitor = get_project_subscription(detector)
        uptime_subscription: UptimeSubscription = uptime_monitor.uptime_subscription

        if uptime_monitor.status == ObjectStatus.DISABLED and not detector.enabled:
            return

        if uptime_subscription.uptime_status == UptimeStatus.FAILED:
            # Resolve the issue so that we don't see it in the ui anymore
            resolve_uptime_issue(detector)

        # We set the status back to ok here so that if we re-enable we'll start
        # from a good state
        uptime_subscription.update(uptime_status=UptimeStatus.OK)

        uptime_monitor.update(status=ObjectStatus.DISABLED)
        detector.update(enabled=False)

        if not skip_quotas:
            quotas.backend.disable_seat(DataCategory.UPTIME, uptime_monitor)

        # Are there any other project subscriptions associated to the subscription
        # that are NOT disabled?
        has_active_subscription = uptime_subscription.projectuptimesubscription_set.exclude(
            status=ObjectStatus.DISABLED
        ).exists()

        # All project subscriptions are disabled, we can disable the subscription
        # and remove the remote subscription.
        if not has_active_subscription:
            uptime_subscription.update(status=UptimeSubscription.Status.DISABLED.value)
            delete_remote_uptime_subscription.delay(uptime_subscription.id)


def enable_uptime_detector(
    detector: Detector, ensure_assignment: bool = False, skip_quotas: bool = False
):
    """
    Enable a uptime detector. If the uptime subscription was also disabled it
    will be re-activated and the remote subscription will be published.

    This method will attempt seat assignment via the quotas system. If There
    are no available seats the monitor will be disabled and a
    `UptimeMonitorNoSeatAvailable` will be raised.

    By default if the monitor is already marked as ACTIVE this function is a
    no-op. Pass `ensure_assignment=True` to force seat assignment.
    """
    uptime_monitor = get_project_subscription(detector)

    if (
        not ensure_assignment
        and uptime_monitor.status != ObjectStatus.DISABLED
        and detector.enabled
    ):
        return

    if not skip_quotas:
        seat_assignment = quotas.backend.check_assign_seat(DataCategory.UPTIME, uptime_monitor)
        if not seat_assignment.assignable:
            disable_uptime_detector(detector)
            raise UptimeMonitorNoSeatAvailable(seat_assignment)

        outcome = quotas.backend.assign_seat(DataCategory.UPTIME, uptime_monitor)
        if outcome != Outcome.ACCEPTED:
            # Race condition, we were unable to assign the seat even though the
            # earlier assignment check indicated assignability
            disable_uptime_detector(detector)
            raise UptimeMonitorNoSeatAvailable(None)

    uptime_subscription: UptimeSubscription = uptime_monitor.uptime_subscription
    uptime_monitor.update(status=ObjectStatus.ACTIVE)
    detector.update(enabled=True)

    # The subscription was disabled, it can be re-activated now
    if uptime_subscription.status == UptimeSubscription.Status.DISABLED.value:
        uptime_subscription.update(status=UptimeSubscription.Status.CREATING.value)
        create_remote_uptime_subscription.delay(uptime_subscription.id)


def delete_uptime_detector(detector: Detector):
    uptime_monitor = get_project_subscription(detector)
    delete_project_uptime_subscription(uptime_monitor)
    RegionScheduledDeletion.schedule(detector, days=0)


def delete_project_uptime_subscription(uptime_monitor: ProjectUptimeSubscription):
    uptime_subscription: UptimeSubscription = uptime_monitor.uptime_subscription
    quotas.backend.remove_seat(DataCategory.UPTIME, uptime_monitor)
    uptime_monitor.delete()
    remove_uptime_subscription_if_unused(uptime_subscription)


def remove_uptime_subscription_if_unused(uptime_subscription: UptimeSubscription):
    """
    Determines if an uptime subscription is no longer used by any `ProjectUptimeSubscriptions` and removes it if so
    """
    # If the uptime subscription is no longer used, we also remove it.
    if not uptime_subscription.projectuptimesubscription_set.exists():
        delete_uptime_subscription(uptime_subscription)


def is_url_auto_monitored_for_project(project: Project, url: str) -> bool:
    auto_detected_subscription_ids = list(
        Detector.objects.filter(
            type=UptimeDomainCheckFailure.slug,
            project=project,
            config__mode__in=(
                UptimeMonitorMode.AUTO_DETECTED_ONBOARDING.value,
                UptimeMonitorMode.AUTO_DETECTED_ACTIVE.value,
            ),
        )
        .select_related("data_sources")
        .values_list("data_sources__source_id", flat=True)
    )

    return UptimeSubscription.objects.filter(
        id__in=auto_detected_subscription_ids,
        url=url,
    ).exists()


def get_auto_monitored_detectors_for_project(
    project: Project,
    modes: Sequence[UptimeMonitorMode] | None = None,
) -> list[Detector]:
    if modes is None:
        modes = [
            UptimeMonitorMode.AUTO_DETECTED_ONBOARDING,
            UptimeMonitorMode.AUTO_DETECTED_ACTIVE,
        ]
    return list(
        Detector.objects.filter(
            type=UptimeDomainCheckFailure.slug, project=project, config__mode__in=modes
        )
    )


def check_and_update_regions(
    subscription: UptimeSubscription,
    regions: list[UptimeSubscriptionRegion],
) -> bool:
    """
    This method will check if regions have been added or removed from our region configuration,
    and updates regions associated with this uptime subscription to reflect the new state.
    """
    subscription_region_modes = {
        UptimeRegionWithMode(r.region_slug, UptimeSubscriptionRegion.RegionMode(r.mode))
        for r in regions
    }
    active_regions = set(get_active_regions())
    if subscription_region_modes == active_regions:
        # Regions haven't changed, exit early.
        return False

    new_or_updated_regions = active_regions - subscription_region_modes
    removed_regions = {srm.slug for srm in subscription_region_modes} - {
        ar.slug for ar in active_regions
    }
    for region in new_or_updated_regions:
        UptimeSubscriptionRegion.objects.update_or_create(
            uptime_subscription=subscription,
            region_slug=region.slug,
            defaults={"mode": region.mode},
        )

    if removed_regions:
        for deleted_region in UptimeSubscriptionRegion.objects.filter(
            uptime_subscription=subscription, region_slug__in=removed_regions
        ):
            if subscription.subscription_id:
                # We need to explicitly send deletes here before we remove the region
                send_uptime_config_deletion(
                    deleted_region.region_slug, subscription.subscription_id
                )
            deleted_region.delete()
    return True


class MaxUrlsForDomainReachedException(Exception):
    def __init__(self, domain, suffix, max_urls):
        self.domain = domain
        self.suffix = suffix
        self.max_urls = max_urls


def check_url_limits(url):
    """
    Determines if a URL's domain has reached the global maximum (MAX_MONITORS_PER_DOMAIN).
    In the case that it has a `MaxUrlsForDomainReachedException` will be raised.
    """
    url_parts = extract_domain_parts(url)
    existing_count = UptimeSubscription.objects.filter(
        url_domain=url_parts.domain,
        url_domain_suffix=url_parts.suffix,
    ).count()

    if existing_count >= MAX_MONITORS_PER_DOMAIN:
        raise MaxUrlsForDomainReachedException(
            url_parts.domain, url_parts.suffix, MAX_MONITORS_PER_DOMAIN
        )
