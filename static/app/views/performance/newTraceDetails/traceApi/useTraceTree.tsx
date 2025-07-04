import {useEffect, useState} from 'react';

import type {QueryStatus, UseApiQueryResult} from 'sentry/utils/queryClient';
import useApi from 'sentry/utils/useApi';
import useOrganization from 'sentry/utils/useOrganization';
import useProjects from 'sentry/utils/useProjects';
import {traceAnalytics} from 'sentry/views/performance/newTraceDetails/traceAnalytics';
import {TraceTree} from 'sentry/views/performance/newTraceDetails/traceModels/traceTree';
import {useTraceState} from 'sentry/views/performance/newTraceDetails/traceState/traceStateProvider';
import type {HydratedReplayRecord} from 'sentry/views/replays/types';

import type {TraceMetaQueryResults} from './useTraceMeta';
import {isEmptyTrace} from './utils';

type UseTraceTreeParams = {
  meta: TraceMetaQueryResults;
  replay: HydratedReplayRecord | null;
  trace: UseApiQueryResult<TraceTree.Trace | undefined, any>;
  traceSlug?: string;
};

function getTraceViewQueryStatus(
  traceQueryStatus: QueryStatus,
  traceMetaQueryStatus: QueryStatus
): QueryStatus {
  if (traceQueryStatus === 'error' || traceMetaQueryStatus === 'error') {
    return 'error';
  }

  if (traceQueryStatus === 'pending' || traceMetaQueryStatus === 'pending') {
    return 'pending';
  }

  return 'success';
}

export function useTraceTree({
  trace,
  meta,
  replay,
  traceSlug,
}: UseTraceTreeParams): TraceTree {
  const api = useApi();
  const {projects} = useProjects();
  const organization = useOrganization();
  const traceState = useTraceState();

  const [tree, setTree] = useState<TraceTree>(TraceTree.Empty());

  const traceWaterfallSource = replay ? 'replay_details' : 'trace_view';

  useEffect(() => {
    const status = getTraceViewQueryStatus(trace.status, meta.status);

    if (status === 'error') {
      setTree(t =>
        t.type === 'error'
          ? t
          : TraceTree.Error({
              project_slug: projects?.[0]?.slug ?? '',
              event_id: traceSlug,
            })
      );
      traceAnalytics.trackTraceErrorState(organization, traceWaterfallSource);
      return;
    }

    if (trace.data && isEmptyTrace(trace.data)) {
      setTree(t => (t.type === 'empty' ? t : TraceTree.Empty()));
      traceAnalytics.trackTraceEmptyState(organization, traceWaterfallSource);
      return;
    }

    if (status === 'pending') {
      setTree(t =>
        t.type === 'loading'
          ? t
          : TraceTree.Loading({
              project_slug: projects?.[0]?.slug ?? '',
              event_id: traceSlug,
            })
      );
      return;
    }

    if (trace.data && meta.data) {
      const newTree = TraceTree.FromTrace(trace.data, {
        meta: meta.data,
        replay,
        preferences: traceState.preferences,
      });

      setTree(newTree);
      newTree.build();
      return;
    }

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    api,
    organization,
    projects,
    replay,
    meta.status,
    trace.status,
    trace.data,
    meta.data,
    traceSlug,
    traceWaterfallSource,
  ]);

  return tree;
}
