import {Fragment, useMemo} from 'react';
import styled from '@emotion/styled';

import Pagination from 'sentry/components/pagination';
import {t, tct} from 'sentry/locale';
import {trackAnalytics} from 'sentry/utils/analytics';
import {decodeList, decodeScalar, decodeSorts} from 'sentry/utils/queryString';
import useFetchReplayList from 'sentry/utils/replays/hooks/useFetchReplayList';
import useReplayListQueryKey from 'sentry/utils/replays/hooks/useReplayListQueryKey';
import {MIN_REPLAY_CLICK_SDK} from 'sentry/utils/replays/sdkVersions';
import {MutableSearch} from 'sentry/utils/tokenizeSearch';
import useLocationQuery from 'sentry/utils/url/useLocationQuery';
import {useNavigate} from 'sentry/utils/useNavigate';
import useOrganization from 'sentry/utils/useOrganization';
import usePageFilters from 'sentry/utils/usePageFilters';
import useProjectSdkNeedsUpdate from 'sentry/utils/useProjectSdkNeedsUpdate';
import useAllMobileProj from 'sentry/views/replays/detail/useAllMobileProj';
import {
  JetpackComposePiiNotice,
  useNeedsJetpackComposePiiNotice,
} from 'sentry/views/replays/jetpackComposePiiNotice';
import ReplayTable from 'sentry/views/replays/replayTable';
import {ReplayColumn} from 'sentry/views/replays/replayTable/types';

function ReplaysList() {
  const organization = useOrganization();
  const navigate = useNavigate();

  const query = useLocationQuery({
    fields: {
      cursor: decodeScalar,
      end: decodeScalar,
      environment: decodeList,
      project: decodeList,
      query: decodeScalar,
      sort: (value: any) => decodeScalar(value, '-started_at'),
      start: decodeScalar,
      statsPeriod: decodeScalar,
      utc: decodeScalar,
    },
  });

  const queryKey = useReplayListQueryKey({
    options: {query},
    organization,
    queryReferrer: 'replayList',
  });
  const {
    data: replays,
    getResponseHeader,
    isPending,
    error,
  } = useFetchReplayList({queryKey});
  const pageLinks = getResponseHeader?.('Link') ?? null;

  const {
    selection: {projects},
  } = usePageFilters();

  const {allMobileProj} = useAllMobileProj({});

  const {needsUpdate: allSelectedProjectsNeedUpdates} = useProjectSdkNeedsUpdate({
    minVersion: MIN_REPLAY_CLICK_SDK.minVersion,
    organization,
    projectId: projects.map(String),
  });

  const conditions = useMemo(() => new MutableSearch(query.query), [query.query]);
  const hasReplayClick = conditions.getFilterKeys().some(k => k.startsWith('click.'));

  // browser isn't applicable for mobile projects
  // rage and dead clicks not available yet
  const visibleCols = allMobileProj
    ? [
        ReplayColumn.REPLAY,
        ReplayColumn.OS,
        ReplayColumn.DURATION,
        ReplayColumn.COUNT_ERRORS,
        ReplayColumn.ACTIVITY,
      ]
    : [
        ReplayColumn.REPLAY,
        ReplayColumn.OS,
        ReplayColumn.BROWSER,
        ReplayColumn.DURATION,
        ReplayColumn.COUNT_DEAD_CLICKS,
        ReplayColumn.COUNT_RAGE_CLICKS,
        ReplayColumn.COUNT_ERRORS,
        ReplayColumn.ACTIVITY,
      ];

  const needsJetpackComposePiiWarning = useNeedsJetpackComposePiiNotice({
    replays,
  });

  return (
    <Fragment>
      {needsJetpackComposePiiWarning && <JetpackComposePiiNotice />}
      <ReplayTable
        referrerLocation={'replay'}
        fetchError={error}
        isFetching={isPending}
        replays={replays}
        sort={decodeSorts(query.sort).at(0)}
        visibleColumns={visibleCols}
        showDropdownFilters
        emptyMessage={
          allSelectedProjectsNeedUpdates && hasReplayClick ? (
            <Fragment>
              {t('Unindexed search field')}
              <EmptyStateSubheading>
                {tct('Field [field] requires an [sdkPrompt]', {
                  field: <strong>'click'</strong>,
                  sdkPrompt: (
                    <strong>
                      {t('SDK version >= %s', MIN_REPLAY_CLICK_SDK.minVersion)}
                    </strong>
                  ),
                })}
              </EmptyStateSubheading>
            </Fragment>
          ) : undefined
        }
      />
      <ReplayPagination
        pageLinks={pageLinks}
        onCursor={(cursor, path, searchQuery) => {
          trackAnalytics('replay.list-paginated', {
            organization,
            direction: cursor?.endsWith(':1') ? 'prev' : 'next',
          });
          navigate({
            pathname: path,
            query: {...searchQuery, cursor},
          });
        }}
      />
    </Fragment>
  );
}

const EmptyStateSubheading = styled('div')`
  color: ${p => p.theme.subText};
  font-size: ${p => p.theme.fontSize.md};
`;

const ReplayPagination = styled(Pagination)`
  margin-top: 0;
`;

export default ReplaysList;
