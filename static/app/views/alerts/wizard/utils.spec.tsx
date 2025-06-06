import {Dataset, SessionsAggregate} from 'sentry/views/alerts/rules/metric/types';
import {getAlertTypeFromAggregateDataset} from 'sentry/views/alerts/wizard/utils';

describe('Wizard utils', function () {
  it('extracts lcp alert', function () {
    expect(
      getAlertTypeFromAggregateDataset({
        aggregate: 'p95(measurements.lcp)',
        dataset: Dataset.TRANSACTIONS,
      })
    ).toBe('lcp');
    expect(
      getAlertTypeFromAggregateDataset({
        aggregate: 'percentile(measurements.lcp,0.7)',
        dataset: Dataset.TRANSACTIONS,
      })
    ).toBe('lcp');
    expect(
      getAlertTypeFromAggregateDataset({
        aggregate: 'avg(measurements.lcp)',
        dataset: Dataset.TRANSACTIONS,
      })
    ).toBe('lcp');
  });

  it('extracts duration alert', function () {
    expect(
      getAlertTypeFromAggregateDataset({
        aggregate: 'p95(transaction.duration)',
        dataset: Dataset.TRANSACTIONS,
      })
    ).toBe('trans_duration');
    expect(
      getAlertTypeFromAggregateDataset({
        aggregate: 'percentile(transaction.duration,0.3)',
        dataset: Dataset.TRANSACTIONS,
      })
    ).toBe('trans_duration');
    expect(
      getAlertTypeFromAggregateDataset({
        aggregate: 'avg(transaction.duration)',
        dataset: Dataset.TRANSACTIONS,
      })
    ).toBe('trans_duration');
  });

  it('extracts throughput alert', function () {
    expect(
      getAlertTypeFromAggregateDataset({
        aggregate: 'count()',
        dataset: Dataset.TRANSACTIONS,
      })
    ).toBe('throughput');
  });

  it('extracts user error alert', function () {
    expect(
      getAlertTypeFromAggregateDataset({
        aggregate: 'count_unique(user)',
        dataset: Dataset.ERRORS,
      })
    ).toBe('users_experiencing_errors');
  });

  it('extracts error count alert', function () {
    expect(
      getAlertTypeFromAggregateDataset({
        aggregate: 'count()',
        dataset: Dataset.ERRORS,
      })
    ).toBe('num_errors');
  });

  it('extracts crash free sessions alert', function () {
    expect(
      getAlertTypeFromAggregateDataset({
        aggregate: SessionsAggregate.CRASH_FREE_SESSIONS,
        dataset: Dataset.METRICS,
      })
    ).toBe('crash_free_sessions');
  });

  it('extracts crash free users alert', function () {
    expect(
      getAlertTypeFromAggregateDataset({
        aggregate: SessionsAggregate.CRASH_FREE_USERS,
        dataset: Dataset.METRICS,
      })
    ).toBe('crash_free_users');
  });

  it('extracts crash free users alert from metrics', function () {
    expect(
      getAlertTypeFromAggregateDataset({
        aggregate: SessionsAggregate.CRASH_FREE_USERS,
        dataset: Dataset.METRICS,
      })
    ).toBe('crash_free_users');
  });

  it('defaults to custom', function () {
    expect(
      getAlertTypeFromAggregateDataset({
        aggregate: 'count_unique(tags[sentry:user])',
        dataset: Dataset.TRANSACTIONS,
      })
    ).toBe('custom_transactions');

    expect(
      getAlertTypeFromAggregateDataset({
        aggregate: 'p95(measurements.fp)',
        dataset: Dataset.TRANSACTIONS,
      })
    ).toBe('custom_transactions');

    expect(
      getAlertTypeFromAggregateDataset({
        aggregate: 'p95(measurements.ttfb)',
        dataset: Dataset.TRANSACTIONS,
      })
    ).toBe('custom_transactions');

    expect(
      getAlertTypeFromAggregateDataset({
        aggregate: 'count(d:transaction/measurement@seconds)',
        dataset: Dataset.GENERIC_METRICS,
      })
    ).toBe('custom_transactions');
  });

  it('extracts eap metric alerts', function () {
    expect(
      getAlertTypeFromAggregateDataset({
        aggregate: 'count(span.duration)',
        dataset: Dataset.EVENTS_ANALYTICS_PLATFORM,
      })
    ).toBe('eap_metrics');
  });
});
