import {Fragment, useMemo, useRef} from 'react';
import styled from '@emotion/styled';

import {CheckInPlaceholder} from 'sentry/components/checkInTimeline/checkInPlaceholder';
import {CheckInTimeline} from 'sentry/components/checkInTimeline/checkInTimeline';
import {
  Gridline,
  GridLineLabels,
  GridLineOverlay,
} from 'sentry/components/checkInTimeline/gridLines';
import type {StatsBucket} from 'sentry/components/checkInTimeline/types';
import {Flex} from 'sentry/components/core/layout';
import {Tooltip} from 'sentry/components/core/tooltip';
import {tct} from 'sentry/locale';
import type {Event} from 'sentry/types/event';
import type {Group} from 'sentry/types/group';
import {useApiQuery} from 'sentry/utils/queryClient';
import {useDebouncedValue} from 'sentry/utils/useDebouncedValue';
import {useDimensions} from 'sentry/utils/useDimensions';
import useOrganization from 'sentry/utils/useOrganization';
import {useUser} from 'sentry/utils/useUser';
import {MonitorIndicator} from 'sentry/views/insights/crons/components/monitorIndicator';
import {CheckInStatus, type MonitorBucket} from 'sentry/views/insights/crons/types';
import {
  checkInStatusPrecedent,
  statusToText,
  tickStyle,
} from 'sentry/views/insights/crons/utils';
import {selectCheckInData} from 'sentry/views/insights/crons/utils/selectCheckInData';
import {useMonitorStats} from 'sentry/views/insights/crons/utils/useMonitorStats';
import {useIssueDetails} from 'sentry/views/issueDetails/streamline/context';
import {useIssueTimeWindowConfig} from 'sentry/views/issueDetails/streamline/useIssueTimeWindowConfig';
import {getGroupEventQueryKey} from 'sentry/views/issueDetails/utils';

export function useCronIssueAlertId({groupId}: {groupId: string}): string | undefined {
  /**
   * This should be removed once the cron rule value is set on the issue.
   * This will fetch an event from the max range if the detector details
   * are not available (e.g. time range has changed and page refreshed)
   */
  const user = useUser();
  const organization = useOrganization();
  const {detectorDetails} = useIssueDetails();
  const {detectorId, detectorType} = detectorDetails;

  const hasCronDetector = detectorId && detectorType === 'cron_monitor';

  const {data: event} = useApiQuery<Event>(
    getGroupEventQueryKey({
      orgSlug: organization.slug,
      groupId,
      eventId: user.options.defaultIssueEvent,
      environments: [],
    }),
    {
      staleTime: Infinity,
      enabled: !hasCronDetector,
      retry: false,
    }
  );

  // Fall back to the fetched event since the legacy UI isn't nested within the provider the provider
  return hasCronDetector
    ? detectorId
    : event?.tags?.find(({key}) => key === 'monitor.id')?.value;
}

function useCronLegendStatuses({
  bucketStats,
}: {
  bucketStats: MonitorBucket[];
}): CheckInStatus[] {
  /**
   * Extract a list of statuses that have occurred at least once in the bucket stats.
   */
  return useMemo(() => {
    const statusMap: Record<CheckInStatus, boolean> = {
      [CheckInStatus.OK]: true,
      [CheckInStatus.ERROR]: false,
      [CheckInStatus.IN_PROGRESS]: false,
      [CheckInStatus.MISSED]: false,
      [CheckInStatus.TIMEOUT]: false,
      [CheckInStatus.UNKNOWN]: false,
    };
    bucketStats?.forEach(([_timestamp, bucketEnvMapping]) => {
      const bucketEnvMappingEntries: Array<StatsBucket<CheckInStatus>> =
        Object.values(bucketEnvMapping);
      for (const statBucket of bucketEnvMappingEntries) {
        const statBucketEntries = Object.entries(statBucket) as Array<
          [CheckInStatus, number]
        >;
        for (const [status, count] of statBucketEntries) {
          if (count > 0 && !statusMap[status]) {
            statusMap[status] = true;
          }
        }
      }
    });
    return (Object.keys(statusMap) as CheckInStatus[]).filter(
      status => statusMap[status]
    );
  }, [bucketStats]);
}

export function IssueCronCheckTimeline({group}: {group: Group}) {
  const elementRef = useRef<HTMLDivElement>(null);
  const {width: containerWidth} = useDimensions<HTMLDivElement>({elementRef});
  const timelineWidth = useDebouncedValue(containerWidth, 500);
  const timeWindowConfig = useIssueTimeWindowConfig({timelineWidth, group});

  const cronAlertId = useCronIssueAlertId({groupId: group.id});
  const {data: stats, isPending} = useMonitorStats({
    monitors: cronAlertId ? [cronAlertId] : [],
    timeWindowConfig,
  });

  const cronStats = useMemo(() => {
    if (!cronAlertId) {
      return [];
    }
    return stats?.[cronAlertId] ?? [];
  }, [cronAlertId, stats]);

  const statEnvironments = useMemo(() => {
    const envSet = cronStats.reduce((acc, [_, envs]) => {
      Object.keys(envs).forEach(env => acc.add(env));
      return acc;
    }, new Set<string>());
    return [...envSet];
  }, [cronStats]);

  const legendStatuses = useCronLegendStatuses({
    bucketStats: cronStats,
  });

  return (
    <ChartContainer envCount={statEnvironments.length}>
      <TimelineLegend ref={elementRef} role="caption">
        {!isPending &&
          legendStatuses.map(status => (
            <Flex align="center" gap="xs" key={status}>
              <MonitorIndicator status={status} size={8} />
              <TimelineLegendText>{statusToText[status]}</TimelineLegendText>
            </Flex>
          ))}
      </TimelineLegend>
      <IssueGridLineOverlay
        allowZoom
        showCursor
        timeWindowConfig={timeWindowConfig}
        labelPosition="center-bottom"
        envCount={statEnvironments.length}
        cursorOverlayAnchor="bottom"
        cursorOverlayAnchorOffset={4}
      />
      <IssueGridLineLabels
        timeWindowConfig={timeWindowConfig}
        labelPosition="center-bottom"
        envCount={statEnvironments.length}
      />
      <TimelineContainer>
        {isPending ? (
          <CheckInPlaceholder />
        ) : (
          <Fragment>
            {statEnvironments.map((env, envIndex) => (
              <Fragment key={env}>
                {statEnvironments.length > 1 && (
                  <EnvironmentLabel
                    title={tct('Environment: [env]', {env})}
                    style={{
                      top: envIndex * totalHeight + timelineHeight,
                    }}
                  >
                    {env}
                  </EnvironmentLabel>
                )}
                <CheckInTimeline
                  style={{
                    top: envIndex * (environmentHeight + paddingHeight),
                  }}
                  bucketedData={stats && env ? selectCheckInData(cronStats, env) : []}
                  statusLabel={statusToText}
                  statusStyle={tickStyle}
                  statusPrecedent={checkInStatusPrecedent}
                  timeWindowConfig={timeWindowConfig}
                />
              </Fragment>
            ))}
          </Fragment>
        )}
      </TimelineContainer>
    </ChartContainer>
  );
}

const timelineHeight = 14;
const environmentHeight = 16;
const paddingHeight = 8;
const totalHeight = timelineHeight + environmentHeight + paddingHeight;

const ChartContainer = styled('div')<{envCount: number}>`
  position: relative;
  width: 100%;
  min-height: ${p => Math.max(p.envCount - 1, 0) * totalHeight + 104}px;
  padding-left: ${p => p.theme.space.lg};
  padding-right: ${p => p.theme.space.lg};
`;

const TimelineLegend = styled('div')`
  position: absolute;
  width: calc(100% - ${p => p.theme.space.lg} * 2);
  user-select: none;
  display: flex;
  gap: ${p => p.theme.space.md};
  margin-top: ${p => p.theme.space.lg};
`;

const TimelineLegendText = styled('div')`
  color: ${p => p.theme.subText};
  font-size: ${p => p.theme.fontSize.sm};
`;

const TimelineContainer = styled('div')`
  position: absolute;
  top: 36px;
  left: ${p => p.theme.space.lg};
  right: ${p => p.theme.space.lg};
  width: calc(100% - ${p => p.theme.space.lg} * 2);
`;

const EnvironmentLabel = styled(Tooltip)`
  position: absolute;
  user-select: none;
  left: 0;
  font-weight: ${p => p.theme.fontWeight.bold};
  font-size: ${p => p.theme.fontSize.xs};
  color: ${p => p.theme.subText};
  white-space: nowrap;
`;

const IssueGridLineLabels = styled(GridLineLabels)<{envCount: number}>`
  top: ${p => Math.max(p.envCount - 1, 0) * totalHeight + 68}px;
`;

const IssueGridLineOverlay = styled(GridLineOverlay)<{envCount: number}>`
  ${Gridline} {
    top: ${p => Math.max(p.envCount - 1, 0) * totalHeight + 68}px;
  }
  width: calc(100% - ${p => p.theme.space.lg} * 2);
`;
