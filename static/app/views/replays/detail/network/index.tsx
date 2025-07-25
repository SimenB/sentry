import {useCallback, useMemo, useRef, useState} from 'react';
import type {GridCellProps} from 'react-virtualized';
import {AutoSizer, CellMeasurer, MultiGrid} from 'react-virtualized';

import {Flex} from 'sentry/components/core/layout/flex';
import {ExternalLink} from 'sentry/components/core/link';
import Placeholder from 'sentry/components/placeholder';
import JumpButtons from 'sentry/components/replays/jumpButtons';
import {useReplayContext} from 'sentry/components/replays/replayContext';
import useJumpButtons from 'sentry/components/replays/useJumpButtons';
import {GridTable} from 'sentry/components/replays/virtualizedGrid/gridTable';
import {OverflowHidden} from 'sentry/components/replays/virtualizedGrid/overflowHidden';
import {SplitPanel} from 'sentry/components/replays/virtualizedGrid/splitPanel';
import useDetailsSplit from 'sentry/components/replays/virtualizedGrid/useDetailsSplit';
import {t, tct} from 'sentry/locale';
import {trackAnalytics} from 'sentry/utils/analytics';
import useCrumbHandlers from 'sentry/utils/replays/hooks/useCrumbHandlers';
import {useReplayReader} from 'sentry/utils/replays/playback/providers/replayReaderProvider';
import useCurrentHoverTime from 'sentry/utils/replays/playback/providers/useCurrentHoverTime';
import {getFrameMethod, getFrameStatus} from 'sentry/utils/replays/resourceFrame';
import useOrganization from 'sentry/utils/useOrganization';
import FilterLoadingIndicator from 'sentry/views/replays/detail/filterLoadingIndicator';
import NetworkDetails from 'sentry/views/replays/detail/network/details';
import NetworkFilters from 'sentry/views/replays/detail/network/networkFilters';
import NetworkHeaderCell, {
  COLUMN_COUNT,
} from 'sentry/views/replays/detail/network/networkHeaderCell';
import NetworkTableCell from 'sentry/views/replays/detail/network/networkTableCell';
import useNetworkFilters from 'sentry/views/replays/detail/network/useNetworkFilters';
import useSortNetwork from 'sentry/views/replays/detail/network/useSortNetwork';
import NoRowRenderer from 'sentry/views/replays/detail/noRowRenderer';
import useVirtualizedGrid from 'sentry/views/replays/detail/useVirtualizedGrid';

const HEADER_HEIGHT = 25;
const BODY_HEIGHT = 25;

const RESIZEABLE_HANDLE_HEIGHT = 90;

const cellMeasurer = {
  defaultHeight: BODY_HEIGHT,
  defaultWidth: 100,
  fixedHeight: true,
};

export default function NetworkList() {
  const organization = useOrganization();
  const replay = useReplayReader();
  const {currentTime} = useReplayContext();
  const [currentHoverTime] = useCurrentHoverTime();
  const {onMouseEnter, onMouseLeave, onClickTimestamp} = useCrumbHandlers();

  const isNetworkDetailsSetup = Boolean(replay?.isNetworkDetailsSetup());
  const isCaptureBodySetup = Boolean(replay?.isNetworkCaptureBodySetup());
  const networkFrames = replay?.getNetworkFrames();
  const projectId = replay?.getReplay()?.project_id;
  const startTimestampMs = replay?.getReplay()?.started_at?.getTime() || 0;

  const [scrollToRow, setScrollToRow] = useState<undefined | number>(undefined);

  const filterProps = useNetworkFilters({networkFrames: networkFrames || []});
  const {items: filteredItems, searchTerm, setSearchTerm} = filterProps;
  const clearSearchTerm = () => setSearchTerm('');
  const {handleSort, items, sortConfig} = useSortNetwork({items: filteredItems});

  const containerRef = useRef<HTMLDivElement>(null);
  const gridRef = useRef<MultiGrid>(null);
  const deps = useMemo(() => [items, searchTerm], [items, searchTerm]);
  const {cache, getColumnWidth, onScrollbarPresenceChange, onWrapperResize} =
    useVirtualizedGrid({
      cellMeasurer,
      gridRef,
      columnCount: COLUMN_COUNT,
      dynamicColumnIndex: 2,
      deps,
    });

  const {
    onClickCell,
    onCloseDetailsSplit,
    resizableDrawerProps,
    selectedIndex,
    splitSize,
  } = useDetailsSplit({
    containerRef,
    frames: networkFrames,
    handleHeight: RESIZEABLE_HANDLE_HEIGHT,
    urlParamName: 'n_detail_row',
    onShowDetails: useCallback(
      ({dataIndex, rowIndex}: any) => {
        setScrollToRow(rowIndex);

        const item = items[dataIndex];
        trackAnalytics('replay.details-network-panel-opened', {
          is_sdk_setup: isNetworkDetailsSetup,
          organization,
          resource_method: getFrameMethod(item!),
          resource_status: String(getFrameStatus(item!)),
          resource_type: item!.op,
        });
      },
      [organization, items, isNetworkDetailsSetup]
    ),
    onHideDetails: useCallback(() => {
      trackAnalytics('replay.details-network-panel-closed', {
        is_sdk_setup: isNetworkDetailsSetup,
        organization,
      });
    }, [organization, isNetworkDetailsSetup]),
  });

  const {
    handleClick: onClickToJump,
    onSectionRendered,
    showJumpDownButton,
    showJumpUpButton,
  } = useJumpButtons({
    currentTime,
    frames: filteredItems,
    isTable: true,
    setScrollToRow,
  });

  const cellRenderer = ({columnIndex, rowIndex, key, style, parent}: GridCellProps) => {
    const network = items[rowIndex - 1]!;

    return (
      <CellMeasurer
        cache={cache}
        columnIndex={columnIndex}
        key={key}
        parent={parent}
        rowIndex={rowIndex}
      >
        {({measure: _, registerChild}) =>
          rowIndex === 0 ? (
            <NetworkHeaderCell
              ref={e => {
                if (e) {
                  registerChild(e);
                }
              }}
              handleSort={handleSort}
              index={columnIndex}
              sortConfig={sortConfig}
              style={{...style, height: HEADER_HEIGHT}}
            />
          ) : (
            <NetworkTableCell
              columnIndex={columnIndex}
              currentHoverTime={currentHoverTime}
              currentTime={currentTime}
              frame={network}
              onMouseEnter={onMouseEnter}
              onMouseLeave={onMouseLeave}
              onClickCell={onClickCell}
              onClickTimestamp={onClickTimestamp}
              ref={e => {
                if (e) {
                  registerChild(e);
                }
              }}
              rowIndex={rowIndex}
              sortConfig={sortConfig}
              startTimestampMs={startTimestampMs}
              style={{...style, height: BODY_HEIGHT}}
            />
          )
        }
      </CellMeasurer>
    );
  };

  return (
    <Flex direction="column" wrap="nowrap">
      <FilterLoadingIndicator isLoading={!replay}>
        <NetworkFilters networkFrames={networkFrames} {...filterProps} />
      </FilterLoadingIndicator>
      <GridTable ref={containerRef} data-test-id="replay-details-network-tab">
        <SplitPanel
          style={{
            gridTemplateRows: splitSize === undefined ? '1fr' : `1fr auto ${splitSize}px`,
          }}
        >
          {networkFrames ? (
            <OverflowHidden>
              <AutoSizer onResize={onWrapperResize}>
                {({height, width}) => (
                  <MultiGrid
                    ref={gridRef}
                    cellRenderer={cellRenderer}
                    columnCount={COLUMN_COUNT}
                    columnWidth={getColumnWidth(width)}
                    deferredMeasurementCache={cache}
                    estimatedColumnSize={100}
                    estimatedRowSize={BODY_HEIGHT}
                    fixedRowCount={1}
                    height={height}
                    noContentRenderer={() => (
                      <NoRowRenderer
                        unfilteredItems={networkFrames}
                        clearSearchTerm={clearSearchTerm}
                      >
                        {replay?.getReplay()?.sdk.name?.includes('flutter')
                          ? tct(
                              'No network requests recorded. Make sure you are using either the [link1:Sentry Dio] or the [link2:Sentry HTTP] integration.',
                              {
                                link1: (
                                  <ExternalLink href="https://docs.sentry.io/platforms/dart/integrations/dio/" />
                                ),
                                link2: (
                                  <ExternalLink href="https://docs.sentry.io/platforms/dart/integrations/http-integration/" />
                                ),
                              }
                            )
                          : t('No network requests recorded')}
                      </NoRowRenderer>
                    )}
                    onScrollbarPresenceChange={onScrollbarPresenceChange}
                    onScroll={() => {
                      if (scrollToRow !== undefined) {
                        setScrollToRow(undefined);
                      }
                    }}
                    onSectionRendered={onSectionRendered}
                    overscanColumnCount={COLUMN_COUNT}
                    overscanRowCount={5}
                    rowCount={items.length + 1}
                    rowHeight={({index}) => (index === 0 ? HEADER_HEIGHT : BODY_HEIGHT)}
                    scrollToRow={scrollToRow}
                    width={width}
                  />
                )}
              </AutoSizer>
              {sortConfig.by === 'startTimestamp' && items.length ? (
                <JumpButtons
                  jump={showJumpUpButton ? 'up' : showJumpDownButton ? 'down' : undefined}
                  onClick={onClickToJump}
                  tableHeaderHeight={HEADER_HEIGHT}
                />
              ) : null}
            </OverflowHidden>
          ) : (
            <Placeholder height="100%" />
          )}
          <NetworkDetails
            {...resizableDrawerProps}
            isSetup={isNetworkDetailsSetup}
            isCaptureBodySetup={isCaptureBodySetup}
            // @ts-expect-error TS(7015): Element implicitly has an 'any' type because index... Remove this comment to see the full error message
            item={selectedIndex ? items[selectedIndex] : null}
            onClose={onCloseDetailsSplit}
            projectId={projectId}
            startTimestampMs={startTimestampMs}
          />
        </SplitPanel>
      </GridTable>
    </Flex>
  );
}
