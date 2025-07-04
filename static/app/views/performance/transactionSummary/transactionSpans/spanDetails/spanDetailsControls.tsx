import styled from '@emotion/styled';
import type {Location} from 'history';

import {Button} from 'sentry/components/core/button';
import SearchBar from 'sentry/components/events/searchBar';
import {DatePageFilter} from 'sentry/components/organizations/datePageFilter';
import {EnvironmentPageFilter} from 'sentry/components/organizations/environmentPageFilter';
import PageFilterBar from 'sentry/components/organizations/pageFilterBar';
import {t} from 'sentry/locale';
import {space} from 'sentry/styles/space';
import type {Organization} from 'sentry/types/organization';
import type EventView from 'sentry/utils/discover/eventView';
import {removeHistogramQueryStrings} from 'sentry/utils/performance/histogram';
import {decodeScalar} from 'sentry/utils/queryString';
import {useNavigate} from 'sentry/utils/useNavigate';
import {
  SPAN_RELATIVE_PERIODS,
  SPAN_RETENTION_DAYS,
} from 'sentry/views/performance/transactionSummary/transactionSpans/utils';

import {ZoomKeys} from './utils';

interface SpanDetailsControlsProps {
  eventView: EventView;
  location: Location;
  organization: Organization;
}

export default function SpanDetailsControls({
  organization,
  eventView,
  location,
}: SpanDetailsControlsProps) {
  const navigate = useNavigate();
  const query = decodeScalar(location.query.query, '');

  const handleSearchQuery = (searchQuery: string): void => {
    navigate({
      pathname: location.pathname,
      query: {
        ...location.query,
        cursor: undefined,
        query: String(searchQuery).trim() || undefined,
      },
    });
  };

  const handleResetView = () => {
    navigate({
      pathname: location.pathname,
      query: removeHistogramQueryStrings(location, Object.values(ZoomKeys)),
    });
  };

  const isZoomed = () => Object.values(ZoomKeys).some(key => location.query[key]);

  return (
    <FilterActions>
      <PageFilterBar condensed>
        <EnvironmentPageFilter />
        <DatePageFilter
          relativeOptions={SPAN_RELATIVE_PERIODS}
          maxPickableDays={SPAN_RETENTION_DAYS}
        />
      </PageFilterBar>
      <SearchBar
        placeholder={t('Filter Transactions')}
        organization={organization}
        projectIds={eventView.project}
        query={query}
        fields={eventView.fields}
        onSearch={handleSearchQuery}
      />
      <Button onClick={handleResetView} disabled={!isZoomed()}>
        {t('Reset View')}
      </Button>
    </FilterActions>
  );
}

const FilterActions = styled('div')`
  display: grid;
  gap: ${space(2)};
  margin-bottom: ${space(2)};

  @media (min-width: ${p => p.theme.breakpoints.sm}) {
    grid-template-columns: auto 1fr auto;
  }
`;
