import styled from '@emotion/styled';

import {AreaChart} from 'sentry/components/charts/areaChart';
import {useChartZoom} from 'sentry/components/charts/useChartZoom';
import {Alert} from 'sentry/components/core/alert';
import Placeholder from 'sentry/components/placeholder';
import {t} from 'sentry/locale';
import type {Group} from 'sentry/types/group';
import type {Project} from 'sentry/types/project';
import useOrganization from 'sentry/utils/useOrganization';
import type {TimePeriodType} from 'sentry/views/alerts/rules/metric/details/constants';
import type {MetricRule} from 'sentry/views/alerts/rules/metric/types';
import {useMetricRule} from 'sentry/views/alerts/rules/metric/utils/useMetricRule';
import type {Incident} from 'sentry/views/alerts/types';
import {useMetricIncidents} from 'sentry/views/issueDetails/metricIssues/useMetricIncidents';
import {useMetricStatsChart} from 'sentry/views/issueDetails/metricIssues/useMetricStatsChart';
import {
  useMetricIssueAlertId,
  useMetricIssueLegend,
  useMetricTimePeriod,
} from 'sentry/views/issueDetails/metricIssues/utils';

interface MetricIssueChartProps {
  group: Group;
  project: Project;
}

export function MetricIssueChart({group, project}: MetricIssueChartProps) {
  const organization = useOrganization();
  const ruleId = useMetricIssueAlertId({groupId: group.id});
  const timePeriod = useMetricTimePeriod();
  const {
    data: rule,
    isLoading: isRuleLoading,
    isError: isRuleError,
  } = useMetricRule(
    {
      orgSlug: organization.slug,
      ruleId: ruleId ?? '',
      query: {
        expand: 'latestIncident',
      },
    },
    {
      staleTime: Infinity,
      retry: false,
      enabled: !!ruleId,
    }
  );

  const {data: incidents = [], isLoading: isIncidentsLoading} = useMetricIncidents(
    {
      orgSlug: organization.slug,
      query: {
        alertRule: ruleId ?? '',
        start: timePeriod.start,
        end: timePeriod.end,
        project: project.id,
      },
    },
    {
      enabled: !!ruleId,
    }
  );

  if (isRuleLoading || isIncidentsLoading || !rule) {
    return (
      <MetricChartSection>
        <MetricIssuePlaceholder type="loading" />
      </MetricChartSection>
    );
  }

  if (isRuleError) {
    return <MetricIssuePlaceholder type="error" />;
  }

  return (
    <MetricChartSection>
      <MetricIssueChartContent
        rule={rule}
        timePeriod={timePeriod}
        project={project}
        incidents={incidents}
      />
    </MetricChartSection>
  );
}

/**
 * This component is nested to avoid trying to fetch data without a rule or time period.
 */
function MetricIssueChartContent({
  rule,
  timePeriod,
  project,
  incidents,
}: {
  project: Project;
  rule: MetricRule;
  timePeriod: TimePeriodType;
  incidents?: Incident[];
}) {
  const chartZoomProps = useChartZoom({saveOnZoom: true});
  const {chartProps, queryResult} = useMetricStatsChart({
    project,
    rule,
    timePeriod,
    incidents,
    referrer: 'metric-issue-chart',
  });
  const {series = [], yAxis, ...otherChartProps} = chartProps;
  const legend = useMetricIssueLegend({rule, series});

  if (queryResult?.isLoading) {
    return <MetricIssuePlaceholder type="loading" />;
  }

  if (queryResult?.isError) {
    return <MetricIssuePlaceholder type="error" />;
  }

  return (
    <ChartContainer role="figure">
      <AreaChart
        {...otherChartProps}
        series={series}
        legend={{...legend, top: 4, right: 4}}
        height={100}
        grid={{
          top: 20,
          right: 0,
          left: 0,
          bottom: 0,
        }}
        yAxis={{
          ...yAxis,
          splitNumber: 2,
        }}
        {...chartZoomProps}
      />
    </ChartContainer>
  );
}

function MetricIssuePlaceholder({type}: {type: 'loading' | 'error'}) {
  return type === 'loading' ? (
    <PlaceholderContainer>
      <Placeholder height="96px" testId="metric-issue-chart-loading" />
    </PlaceholderContainer>
  ) : (
    <MetricChartAlert type="error" showIcon data-test-id="metric-issue-chart-error">
      {t('Unable to load the metric history')}
    </MetricChartAlert>
  );
}

const MetricChartSection = styled('div')`
  display: block;
  padding-right: ${p => p.theme.space.lg};
  padding-left: ${p => p.theme.space.lg};
  width: 100%;
`;

const PlaceholderContainer = styled('div')`
  padding: ${p => p.theme.space.md} 0;
`;

const ChartContainer = styled('div')`
  position: relative;
  padding: ${p => p.theme.space.sm} 0;
`;

const MetricChartAlert = styled(Alert)`
  width: 100%;
  border: 0;
  border-radius: 0;
`;
