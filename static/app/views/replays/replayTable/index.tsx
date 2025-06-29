import type {ReactNode} from 'react';
import styled from '@emotion/styled';

import {Alert} from 'sentry/components/core/alert';
import LoadingIndicator from 'sentry/components/loadingIndicator';
import {PanelTable} from 'sentry/components/panels/panelTable';
import {useSelectedReplayIndex} from 'sentry/components/replays/queryParams/selectedReplayIndex';
import {t} from 'sentry/locale';
import type {Sort} from 'sentry/utils/discover/fields';
import type RequestError from 'sentry/utils/requestError/requestError';
import {ERROR_MAP} from 'sentry/utils/requestError/requestError';
import type {ReplayListRecordWithTx} from 'sentry/views/performance/transactionSummary/transactionReplays/useReplaysWithTxData';
import HeaderCell from 'sentry/views/replays/replayTable/headerCell';
import {
  ActivityCell,
  BrowserCell,
  DeadClickCountCell,
  DurationCell,
  ErrorCountCell,
  OSCell,
  PlayPauseCell,
  RageClickCountCell,
  ReplayCell,
  TransactionCell,
} from 'sentry/views/replays/replayTable/tableCell';
import {ReplayColumn} from 'sentry/views/replays/replayTable/types';
import type {ReplayListRecord} from 'sentry/views/replays/types';

type Props = {
  fetchError: null | undefined | RequestError;
  isFetching: boolean;
  replays: undefined | ReplayListRecord[] | ReplayListRecordWithTx[];
  sort: Sort | undefined;
  visibleColumns: ReplayColumn[];
  emptyMessage?: ReactNode;
  gridRows?: string;
  onClickRow?: (index: number) => void;
  referrerLocation?: string;
  showDropdownFilters?: boolean;
};

function getErrorMessage(fetchError: RequestError) {
  if (typeof fetchError === 'string') {
    return fetchError;
  }
  if (typeof fetchError?.responseJSON?.detail === 'string') {
    return fetchError.responseJSON.detail;
  }
  if (fetchError?.responseJSON?.detail?.message) {
    return fetchError.responseJSON.detail.message;
  }
  if (fetchError.name === ERROR_MAP[500]) {
    return t('There was an internal systems error.');
  }
  return t(
    'This could be due to invalid search parameters or an internal systems error.'
  );
}

function ReplayTable({
  fetchError,
  isFetching,
  replays,
  sort,
  visibleColumns,
  emptyMessage,
  gridRows,
  showDropdownFilters,
  onClickRow,
  referrerLocation,
}: Props) {
  const {index: selectedReplayIndex} = useSelectedReplayIndex();

  const tableHeaders = visibleColumns
    .filter(Boolean)
    .map(column => <HeaderCell key={column} column={column} sort={sort} />);

  if (fetchError && !isFetching) {
    return (
      <StyledPanelTable
        headers={tableHeaders}
        isLoading={false}
        visibleColumns={visibleColumns}
        data-test-id="replay-table"
        gridRows={undefined}
      >
        <StyledAlert type="error" showIcon>
          {t('Sorry, the list of replays could not be loaded. ')}
          {getErrorMessage(fetchError)}
        </StyledAlert>
      </StyledPanelTable>
    );
  }

  return (
    <StyledPanelTable
      headers={tableHeaders}
      isEmpty={replays?.length === 0}
      isLoading={isFetching}
      visibleColumns={visibleColumns}
      disablePadding
      data-test-id="replay-table"
      emptyMessage={emptyMessage}
      gridRows={isFetching ? undefined : gridRows}
      loader={<StyledLoadingIndicator />}
      disableHeaderBorderBottom
    >
      {replays?.map(
        (replay: ReplayListRecord | ReplayListRecordWithTx, index: number) => {
          return (
            <Row
              key={replay.id}
              isPlaying={index === selectedReplayIndex && referrerLocation !== 'replay'}
              onClick={() => onClickRow?.(index)}
              showCursor={onClickRow !== undefined}
              referrerLocation={referrerLocation}
            >
              {visibleColumns.map(column => {
                switch (column) {
                  case ReplayColumn.ACTIVITY:
                    return (
                      <ActivityCell
                        key="activity"
                        replay={replay}
                        rowIndex={index}
                        showDropdownFilters={showDropdownFilters}
                      />
                    );

                  case ReplayColumn.BROWSER:
                    return (
                      <BrowserCell
                        key="browser"
                        replay={replay}
                        rowIndex={index}
                        showDropdownFilters={showDropdownFilters}
                      />
                    );

                  case ReplayColumn.COUNT_DEAD_CLICKS:
                    return (
                      <DeadClickCountCell
                        key="countDeadClicks"
                        replay={replay}
                        rowIndex={index}
                        showDropdownFilters={showDropdownFilters}
                      />
                    );

                  case ReplayColumn.COUNT_ERRORS:
                    return (
                      <ErrorCountCell
                        key="countErrors"
                        replay={replay}
                        rowIndex={index}
                        showDropdownFilters={showDropdownFilters}
                      />
                    );

                  case ReplayColumn.COUNT_RAGE_CLICKS:
                    return (
                      <RageClickCountCell
                        key="countRageClicks"
                        replay={replay}
                        rowIndex={index}
                        showDropdownFilters={showDropdownFilters}
                      />
                    );

                  case ReplayColumn.DURATION:
                    return (
                      <DurationCell
                        key="duration"
                        replay={replay}
                        rowIndex={index}
                        showDropdownFilters={showDropdownFilters}
                      />
                    );

                  case ReplayColumn.OS:
                    return (
                      <OSCell
                        key="os"
                        replay={replay}
                        rowIndex={index}
                        showDropdownFilters={showDropdownFilters}
                      />
                    );

                  case ReplayColumn.REPLAY:
                    return <ReplayCell key="session" replay={replay} rowIndex={index} />;

                  case ReplayColumn.PLAY_PAUSE:
                    return <PlayPauseCell key="play" replay={replay} rowIndex={index} />;

                  case ReplayColumn.SLOWEST_TRANSACTION:
                    return (
                      <TransactionCell
                        key="slowestTransaction"
                        replay={replay}
                        rowIndex={index}
                      />
                    );

                  default:
                    return null;
                }
              })}
            </Row>
          );
        }
      )}
    </StyledPanelTable>
  );
}

const StyledPanelTable = styled(PanelTable)<{
  visibleColumns: ReplayColumn[];
  gridRows?: string;
}>`
  margin-bottom: 0;
  grid-template-columns: ${p =>
    p.visibleColumns
      .filter(Boolean)
      .map(column => (column === 'replay' ? 'minmax(100px, 1fr)' : 'max-content'))
      .join(' ')};
  ${props =>
    props.gridRows
      ? `grid-template-rows: ${props.gridRows};`
      : `grid-template-rows: 44px max-content;`}
`;

const StyledAlert = styled(Alert)`
  border-radius: 0;
  border-width: 1px 0 0 0;
  grid-column: 1/-1;
`;

const Row = styled('div')<{
  isPlaying?: boolean;
  referrerLocation?: string;
  showCursor?: boolean;
}>`
  ${p =>
    p.referrerLocation === 'replay'
      ? `display: contents;
         & > * {
          border-top: 1px solid ${p.theme.border};
          }`
      : `display: contents;
  & > * {
    background-color: ${p.isPlaying ? p.theme.translucentGray200 : 'inherit'};
    border-top: 1px solid ${p.theme.border};
    cursor: ${p.showCursor ? 'pointer' : 'default'};
  }
  :hover {
    background-color: ${p.showCursor ? p.theme.translucentInnerBorder : 'inherit'};
  }
  :active {
    background-color: ${p.theme.translucentGray200};
  }
  `}
`;

export default ReplayTable;

const StyledLoadingIndicator = styled(LoadingIndicator)`
  margin: 54px auto;
`;
