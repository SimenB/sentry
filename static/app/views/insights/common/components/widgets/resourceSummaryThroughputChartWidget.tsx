import {useParams} from 'sentry/utils/useParams';
import {InsightsLineChartWidget} from 'sentry/views/insights/common/components/insightsLineChartWidget';
import {
  useResourceSummarySeries,
  useResourceSummarySeriesSearch,
} from 'sentry/views/insights/common/components/widgets/hooks/useResourceSummarySeries';
import type {LoadableChartWidgetProps} from 'sentry/views/insights/common/components/widgets/types';
import {getThroughputChartTitle} from 'sentry/views/insights/common/views/spans/types';

export default function ResourceSummaryThroughputChartWidget(
  props: LoadableChartWidgetProps
) {
  const {groupId} = useParams();

  const {search, enabled} = useResourceSummarySeriesSearch(groupId);

  const {data, isPending, error} = useResourceSummarySeries({
    search,
    pageFilters: props.pageFilters,
    enabled,
  });

  return (
    <InsightsLineChartWidget
      {...props}
      queryInfo={{search}}
      id="resourceSummaryThroughputChartWidget"
      title={getThroughputChartTitle('resource')}
      series={[data?.[`epm()`]]}
      isLoading={isPending}
      error={error}
    />
  );
}
