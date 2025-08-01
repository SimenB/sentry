import {Fragment} from 'react';

import DetailsSplitDivider from 'sentry/components/replays/virtualizedGrid/detailsSplitDivider';
import type {SpanFrame} from 'sentry/utils/replays/types';
import useUrlParams from 'sentry/utils/url/useUrlParams';
import type {useResizableDrawer} from 'sentry/utils/useResizableDrawer';
import NetworkDetailsContent from 'sentry/views/replays/detail/network/details/content';
import type {TabKey} from 'sentry/views/replays/detail/network/details/tabs';
import NetworkDetailsTabs from 'sentry/views/replays/detail/network/details/tabs';

type Props = {
  isCaptureBodySetup: boolean;
  isSetup: boolean;
  item: null | SpanFrame;
  onClose: () => void;
  projectId: undefined | string;
  startTimestampMs: number;
} & Omit<ReturnType<typeof useResizableDrawer>, 'size'>;

function NetworkDetails({
  isHeld,
  isSetup,
  isCaptureBodySetup,
  item,
  onClose,
  onDoubleClick,
  onMouseDown,
  projectId,
  startTimestampMs,
}: Props) {
  const {getParamValue: getDetailTab} = useUrlParams('n_detail_tab', 'details');

  if (!item || !projectId) {
    return null;
  }

  const visibleTab = getDetailTab() as TabKey;

  return (
    <Fragment>
      <DetailsSplitDivider
        isHeld={isHeld}
        onClose={onClose}
        onDoubleClick={onDoubleClick}
        onMouseDown={onMouseDown}
      >
        <NetworkDetailsTabs />
      </DetailsSplitDivider>

      <NetworkDetailsContent
        isSetup={isSetup}
        isCaptureBodySetup={isCaptureBodySetup}
        item={item}
        projectId={projectId}
        startTimestampMs={startTimestampMs}
        visibleTab={visibleTab}
      />
    </Fragment>
  );
}

export default NetworkDetails;
