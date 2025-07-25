import type React from 'react';
import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useReducer,
  useRef,
  useState,
} from 'react';
import {flushSync} from 'react-dom';
import styled from '@emotion/styled';
import * as Sentry from '@sentry/react';
import * as qs from 'query-string';

import {addSuccessMessage} from 'sentry/actionCreators/indicator';
import {Flex} from 'sentry/components/core/layout';
import {getRelativeDate} from 'sentry/components/timeSince';
import {t, tct} from 'sentry/locale';
import {space} from 'sentry/styles/space';
import type {Organization} from 'sentry/types/organization';
import type {Project} from 'sentry/types/project';
import {defined} from 'sentry/utils';
import {trackAnalytics} from 'sentry/utils/analytics';
import {browserHistory} from 'sentry/utils/browserHistory';
import {DemoTourElement, DemoTourStep} from 'sentry/utils/demoMode/demoTours';
import type EventView from 'sentry/utils/discover/eventView';
import {
  cancelAnimationTimeout,
  requestAnimationTimeout,
} from 'sentry/utils/profiling/hooks/useVirtualizedTree/virtualizedTreeUtils';
import type {UseApiQueryResult} from 'sentry/utils/queryClient';
import type RequestError from 'sentry/utils/requestError/requestError';
import useApi from 'sentry/utils/useApi';
import type {DispatchingReducerMiddleware} from 'sentry/utils/useDispatchingReducer';
import useOrganization from 'sentry/utils/useOrganization';
import usePageFilters from 'sentry/utils/usePageFilters';
import useProjects from 'sentry/utils/useProjects';
import type {TraceRootEventQueryResults} from 'sentry/views/performance/newTraceDetails/traceApi/useTraceRootEvent';
import {isTraceItemDetailsResponse} from 'sentry/views/performance/newTraceDetails/traceApi/utils';
import {TraceLinkNavigationButton} from 'sentry/views/performance/newTraceDetails/traceLinksNavigation/traceLinkNavigationButton';
import {TraceTree} from 'sentry/views/performance/newTraceDetails/traceModels/traceTree';
import {TraceOpenInExploreButton} from 'sentry/views/performance/newTraceDetails/traceOpenInExploreButton';
import {traceGridCssVariables} from 'sentry/views/performance/newTraceDetails/traceWaterfallStyles';
import {useDividerResizeSync} from 'sentry/views/performance/newTraceDetails/useDividerResizeSync';
import {useIsEAPTraceEnabled} from 'sentry/views/performance/newTraceDetails/useIsEAPTraceEnabled';
import {useTraceQueryParams} from 'sentry/views/performance/newTraceDetails/useTraceQueryParams';
import {useTraceSpaceListeners} from 'sentry/views/performance/newTraceDetails/useTraceSpaceListeners';
import type {useTraceWaterfallModels} from 'sentry/views/performance/newTraceDetails/useTraceWaterfallModels';
import type {useTraceWaterfallScroll} from 'sentry/views/performance/newTraceDetails/useTraceWaterfallScroll';
import type {ReplayTrace} from 'sentry/views/replays/detail/trace/useReplayTraces';
import type {ReplayRecord} from 'sentry/views/replays/types';

import type {TraceMetaQueryResults} from './traceApi/useTraceMeta';
import {TraceDrawer} from './traceDrawer/traceDrawer';
import type {TraceTreeNode} from './traceModels/traceTreeNode';
import {
  searchInTraceTreeText,
  searchInTraceTreeTokens,
} from './traceSearch/traceSearchEvaluator';
import {TraceSearchInput} from './traceSearch/traceSearchInput';
import {parseTraceSearch} from './traceSearch/traceTokenConverter';
import {
  useTraceState,
  useTraceStateDispatch,
  useTraceStateEmitter,
} from './traceState/traceStateProvider';
import {usePerformanceSubscriptionDetails} from './traceTypeWarnings/usePerformanceSubscriptionDetails';
import {Trace} from './trace';
import {traceAnalytics, type TraceWaterFallSource} from './traceAnalytics';
import {
  isAutogroupedNode,
  isEAPTraceNode,
  isParentAutogroupedNode,
  isSiblingAutogroupedNode,
  isTraceNode,
} from './traceGuards';
import {TracePreferencesDropdown} from './tracePreferencesDropdown';
import {TraceResetZoomButton} from './traceResetZoomButton';
import type {TraceReducer, TraceReducerState} from './traceState';
import {
  traceNodeAdjacentAnalyticsProperties,
  traceNodeAnalyticsName,
} from './traceTreeAnalytics';
import TraceTypeWarnings from './traceTypeWarnings';
import {TraceWaterfallState} from './traceWaterfallState';
import {useTraceOnLoad} from './useTraceOnLoad';
import {useTraceQueryParamStateSync} from './useTraceQueryParamStateSync';
import {useTraceScrollToPath} from './useTraceScrollToPath';
import {useTraceTimelineChangeSync} from './useTraceTimelineChangeSync';

const TRACE_TAB: TraceReducerState['tabs']['tabs'][0] = {
  node: 'trace',
  label: t('Trace'),
};

export interface TraceWaterfallProps {
  meta: TraceMetaQueryResults;
  organization: Organization;
  replay: ReplayRecord | null;
  rootEventResults: TraceRootEventQueryResults;
  source: string;
  trace: UseApiQueryResult<TraceTree.Trace, RequestError>;
  traceEventView: EventView;
  traceSlug: string;
  traceWaterfallModels: ReturnType<typeof useTraceWaterfallModels>;
  traceWaterfallScrollHandlers: ReturnType<typeof useTraceWaterfallScroll>;
  tree: TraceTree;
  // If set to true, the entire waterfall will not render if it is empty.
  hideIfNoData?: boolean;
  replayTraces?: ReplayTrace[];
}

export function TraceWaterfall(props: TraceWaterfallProps) {
  const api = useApi();
  const filters = usePageFilters();
  const {projects} = useProjects();
  const organization = useOrganization();

  const isEAP = useIsEAPTraceEnabled();

  const traceDispatch = useTraceStateDispatch();
  const traceStateEmitter = useTraceStateEmitter();

  const traceState = useTraceState();

  const traceStateRef = useRef<TraceReducerState>(traceState);
  traceStateRef.current = traceState;

  const {viewManager, traceScheduler, traceView} = props.traceWaterfallModels;
  const {onScrollToNode, scrollRowIntoView} = props.traceWaterfallScrollHandlers;

  const [forceRender, rerender] = useReducer(x => (x + 1) % Number.MAX_SAFE_INTEGER, 0);

  const projectsRef = useRef<Project[]>(projects);
  projectsRef.current = projects;

  const scrollQueueRef = useTraceScrollToPath();
  const forceRerender = useCallback(() => {
    flushSync(rerender);
  }, []);

  const {timestamp} = useTraceQueryParams();

  const showLinkedTraces = organization?.features.includes('trace-view-linked-traces');

  useEffect(() => {
    trackAnalytics('performance_views.trace_view_v1_page_load', {
      organization: props.organization,
      source: props.source,
    });
  }, [props.organization, props.source]);

  const previouslyFocusedNodeRef = useRef<TraceTreeNode<TraceTree.NodeValue> | null>(
    null
  );
  const previouslyScrolledToNodeRef = useRef<TraceTreeNode<TraceTree.NodeValue> | null>(
    null
  );

  useEffect(() => {
    if (!props.replayTraces?.length || props.tree?.type !== 'trace') {
      return undefined;
    }

    const cleanup = props.tree.fetchAdditionalTraces({
      type: isEAP ? 'eap' : 'non-eap',
      api,
      filters,
      replayTraces: props.replayTraces,
      organization: props.organization,
      urlParams: qs.parse(location.search),
      rerender: forceRerender,
      meta: props.meta,
      preferences: traceState.preferences,
    });

    return () => cleanup();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.tree, props.replayTraces]);

  // Initialize the tabs reducer when the tree initializes
  useLayoutEffect(() => {
    return traceDispatch({
      type: 'set roving count',
      items: props.tree.list.length - 1,
    });
  }, [props.tree.list.length, traceDispatch]);

  // Initialize the tabs reducer when the tree initializes
  useLayoutEffect(() => {
    if (props.tree.type !== 'trace') {
      return;
    }

    traceDispatch({
      type: 'initialize tabs reducer',
      payload: {
        current_tab: traceStateRef?.current?.tabs?.tabs?.[0] ?? null,
        tabs: [],
        last_clicked_tab: null,
      },
    });
    // We only want to update the tabs when the tree changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.tree]);

  const searchingRaf = useRef<{id: number | null} | null>(null);
  const onTraceSearch = useCallback(
    (
      query: string,
      activeNode: TraceTreeNode<TraceTree.NodeValue> | null,
      behavior: 'track result' | 'persist'
    ) => {
      if (searchingRaf.current?.id) {
        window.cancelAnimationFrame(searchingRaf.current.id);
        searchingRaf.current = null;
      }

      // @ts-expect-error TS(7031): Binding element 'matches' implicitly has an 'any' ... Remove this comment to see the full error message
      function done([matches, lookup, activeNodeSearchResult]) {
        // If the previous node is still in the results set, we want to keep it
        if (activeNodeSearchResult) {
          traceDispatch({
            type: 'set results',
            results: matches,
            resultsLookup: lookup,
            resultIteratorIndex: activeNodeSearchResult?.resultIteratorIndex,
            resultIndex: activeNodeSearchResult?.resultIndex,
            previousNode: activeNodeSearchResult,
            node: activeNode,
          });
          return;
        }

        if (activeNode && behavior === 'persist') {
          traceDispatch({
            type: 'set results',
            results: matches,
            resultsLookup: lookup,
            resultIteratorIndex: undefined,
            resultIndex: undefined,
            previousNode: null,
            node: activeNode,
          });
          return;
        }

        const resultIndex: number | undefined = matches?.[0]?.index;
        const resultIteratorIndex: number | undefined = matches?.[0] ? 0 : undefined;
        const node: TraceTreeNode<TraceTree.NodeValue> | null = matches?.[0]?.value;

        traceDispatch({
          type: 'set results',
          results: matches,
          resultsLookup: lookup,
          resultIteratorIndex,
          resultIndex,
          previousNode: activeNodeSearchResult,
          node,
        });
      }

      const tokens = parseTraceSearch(query);

      if (tokens) {
        searchingRaf.current = searchInTraceTreeTokens(
          props.tree,
          tokens,
          activeNode,
          done
        );
      } else {
        searchingRaf.current = searchInTraceTreeText(props.tree, query, activeNode, done);
      }
    },
    [traceDispatch, props.tree]
  );

  // We need to heavily debounce query string updates because the rest of the app is so slow
  // to rerender that it causes the search to drop frames on every keystroke...
  const QUERY_STRING_STATE_DEBOUNCE = 300;
  const queryStringAnimationTimeoutRef = useRef<{id: number} | null>(null);
  const setRowAsFocused = useCallback(
    (
      node: TraceTreeNode<TraceTree.NodeValue> | null,
      event: React.MouseEvent<HTMLElement> | null,
      resultsLookup: Map<TraceTreeNode<TraceTree.NodeValue>, number>,
      index: number | null,
      debounce: number = QUERY_STRING_STATE_DEBOUNCE
    ) => {
      // sync query string with the clicked node
      if (node) {
        if (isTraceNode(node) || isEAPTraceNode(node)) {
          return;
        }

        if (queryStringAnimationTimeoutRef.current) {
          cancelAnimationTimeout(queryStringAnimationTimeoutRef.current);
        }

        queryStringAnimationTimeoutRef.current = requestAnimationTimeout(() => {
          const currentQueryStringPath = qs.parse(location.search).node;
          const nextNodePath = TraceTree.PathToNode(node);
          // Updating the query string with the same path is problematic because it causes
          // the entire sentry app to rerender, which is enough to cause jank and drop frames
          if (JSON.stringify(currentQueryStringPath) === JSON.stringify(nextNodePath)) {
            return;
          }
          const {eventId: _eventId, ...query} = qs.parse(location.search);
          browserHistory.replace({
            pathname: location.pathname,
            query: {
              ...query,
              node: nextNodePath,
            },
          });
          queryStringAnimationTimeoutRef.current = null;
        }, debounce);

        if (resultsLookup.has(node) && typeof index === 'number') {
          traceDispatch({
            type: 'set search iterator index',
            resultIndex: index,
            resultIteratorIndex: resultsLookup.get(node)!,
          });
        }

        if (isTraceNode(node)) {
          traceDispatch({type: 'activate tab', payload: TRACE_TAB.node});
          return;
        }

        traceDispatch({
          type: 'activate tab',
          payload: node,
          pin_previous: event?.metaKey,
        });
      }
    },
    [traceDispatch]
  );

  const onRowClick = useCallback(
    (
      node: TraceTreeNode<TraceTree.NodeValue>,
      event: React.MouseEvent<HTMLElement>,
      index: number
    ) => {
      if (isTraceNode(node) || isEAPTraceNode(node)) {
        traceDispatch({
          type: 'set roving index',
          action_source: 'click',
          index,
          node,
        });
        return;
      }

      trackAnalytics('trace.trace_layout.span_row_click', {
        organization,
        num_children: node.children.length,
        type: traceNodeAnalyticsName(node),
        project_platform:
          projects.find(p => p.slug === node.metadata.project_slug)?.platform || 'other',
        ...traceNodeAdjacentAnalyticsProperties(node),
      });

      if (traceStateRef.current.preferences.drawer.minimized) {
        traceDispatch({type: 'minimize drawer', payload: false});
      }
      setRowAsFocused(node, event, traceStateRef.current.search.resultsLookup, null, 0);

      if (traceStateRef.current.search.resultsLookup.has(node)) {
        const idx = traceStateRef.current.search.resultsLookup.get(node)!;
        traceDispatch({
          type: 'set search iterator index',
          resultIndex: index,
          resultIteratorIndex: idx,
        });
      } else if (traceStateRef.current.search.resultIteratorIndex !== null) {
        traceDispatch({type: 'clear search iterator index'});
      }

      traceDispatch({
        type: 'set roving index',
        action_source: 'click',
        index,
        node,
      });
    },
    [setRowAsFocused, traceDispatch, organization, projects]
  );

  const onTabScrollToNode = useCallback(
    (
      node: TraceTreeNode<TraceTree.NodeValue>
    ): Promise<TraceTreeNode<TraceTree.NodeValue> | null> => {
      return onScrollToNode(node).then(maybeNode => {
        if (maybeNode) {
          setRowAsFocused(
            maybeNode,
            null,
            traceStateRef.current.search.resultsLookup,
            null,
            0
          );
        }

        return maybeNode;
      });
    },
    [onScrollToNode, setRowAsFocused]
  );

  const {
    data: {hasExceededPerformanceUsageLimit},
    isLoading: isLoadingSubscriptionDetails,
  } = usePerformanceSubscriptionDetails();

  const source: TraceWaterFallSource = props.replay ? 'replay_details' : 'trace_view';

  // Callback that is invoked when the trace loads and reaches its initialied state,
  // that is when the trace tree data and any data that the trace depends on is loaded,
  // but the trace is not yet rendered in the view.
  const onTraceLoad = useCallback(() => {
    const traceNode = props.tree.root.children[0];
    const traceTimestamp = traceNode?.space?.[0] ?? (timestamp ? timestamp * 1000 : null);
    const traceAge = defined(traceTimestamp)
      ? getRelativeDate(traceTimestamp, 'ago')
      : 'unknown';

    if (!isLoadingSubscriptionDetails) {
      traceAnalytics.trackTraceShape(
        props.tree,
        projectsRef.current,
        props.organization,
        hasExceededPerformanceUsageLimit,
        source,
        traceAge
      );
    }
    // The tree has the data fetched, but does not yet respect the user preferences.
    // We will autogroup and inject missing instrumentation if the preferences are set.
    // and then we will perform a search to find the node the user is interested in.

    const query = qs.parse(location.search);
    if (query.fov && typeof query.fov === 'string') {
      viewManager.maybeInitializeTraceViewFromQS(query.fov);
    }

    TraceTree.ApplyPreferences(props.tree.root, {
      preferences: traceStateRef.current.preferences,
    });

    // Construct the visual representation of the tree
    props.tree.build();

    const eventId = scrollQueueRef.current?.eventId;
    const [type, path] = scrollQueueRef.current?.path?.[0]?.split('-') ?? [];

    let node =
      (path === 'root' && props.tree.root.children[0]) ||
      (path && TraceTree.FindByID(props.tree.root, path)) ||
      (eventId && TraceTree.FindByID(props.tree.root, eventId)) ||
      null;

    // If the node points to a span, but we found an autogrouped node, then
    // perform another search inside the autogrouped node to find the more detailed
    // location of the span. This is necessary because the id of the autogrouped node
    // is in some cases inferred from the spans it contains and searching by the span id
    // just gives us the first match which may not be the one the user is looking for.
    if (node) {
      if (isAutogroupedNode(node) && type !== 'ag') {
        const id = path ?? eventId!;
        if (isParentAutogroupedNode(node)) {
          node = TraceTree.FindByID(node.head, id) ?? node;
        } else if (isSiblingAutogroupedNode(node)) {
          node = node.children.find(n => TraceTree.FindByID(n, id)) ?? node;
        }
      }
    }

    const index = node ? TraceTree.EnforceVisibility(props.tree, node) : -1;

    if (traceStateRef.current.search.query) {
      onTraceSearch(traceStateRef.current.search.query, node, 'persist');
    }

    if (index === -1 || !node) {
      const hasScrollComponent = !!(path || eventId);
      if (hasScrollComponent) {
        Sentry.withScope(scope => {
          scope.setFingerprint(['trace-view-scroll-to-node-error']);
          scope.captureMessage('Failed to scroll to node in trace tree');
        });
      }

      return;
    }

    // At load time, we want to scroll the row into view, but we need to wait for the view
    // to initialize before we can do that. We listen for the 'initialize virtualized list' and scroll
    // to the row in the view if it is not in view yet. If its in the view, then scroll to it immediately.
    traceScheduler.once('initialize virtualized list', () => {
      function onTargetRowMeasure() {
        if (!node || !viewManager.row_measurer.cache.has(node)) {
          return;
        }
        viewManager.row_measurer.off('row measure end', onTargetRowMeasure);
        if (viewManager.isOutsideOfView(node)) {
          viewManager.scrollRowIntoViewHorizontally(node, 0, 48, 'measured');
        }
      }
      viewManager.scrollToRow(index, 'center');
      viewManager.row_measurer.on('row measure end', onTargetRowMeasure);
      previouslyScrolledToNodeRef.current = node;

      setRowAsFocused(node, null, traceStateRef.current.search.resultsLookup, index);
      traceDispatch({
        type: 'set roving index',
        node,
        index,
        action_source: 'load',
      });
    });

    // TODO Abdullah Khan: Remove this once /trace-meta/ starts responding
    // with the correct spans count for EAP traces.
    if (
      traceNode &&
      isEAPTraceNode(traceNode) &&
      props.tree.eap_spans_count !== props.meta?.data?.span_count
    ) {
      Sentry.withScope(scope => {
        scope.setFingerprint(['trace-eap-spans-count-mismatch']);
        scope.captureMessage(
          'EAP spans count from /trace/ and /trace-meta/ are not equal'
        );
      });
    }
  }, [
    setRowAsFocused,
    traceDispatch,
    onTraceSearch,
    viewManager,
    traceScheduler,
    scrollQueueRef,
    props.tree,
    props.organization,
    isLoadingSubscriptionDetails,
    hasExceededPerformanceUsageLimit,
    props.meta?.data?.span_count,
    source,
    timestamp,
  ]);

  // Setup the middleware for the trace reducer
  useLayoutEffect(() => {
    const beforeTraceNextStateDispatch: DispatchingReducerMiddleware<
      typeof TraceReducer
    >['before next state'] = (prevState, nextState, action) => {
      // This effect is responsible fo syncing the keyboard interactions with the search results,
      // we observe the changes to the roving tab index and search results and react by syncing the state.
      const {node: nextRovingNode, index: nextRovingTabIndex} = nextState.rovingTabIndex;
      const {resultIndex: nextSearchResultIndex} = nextState.search;
      if (
        nextRovingNode &&
        action.type === 'set roving index' &&
        action.action_source !== 'click' &&
        typeof nextRovingTabIndex === 'number' &&
        prevState.rovingTabIndex.node !== nextRovingNode
      ) {
        // When the roving tabIndex updates mark the node as focused and sync search results
        setRowAsFocused(
          nextRovingNode,
          null,
          nextState.search.resultsLookup,
          nextRovingTabIndex
        );
        if (action.type === 'set roving index' && action.action_source === 'keyboard') {
          scrollRowIntoView(nextRovingNode, nextRovingTabIndex, undefined);
        }

        if (nextState.search.resultsLookup.has(nextRovingNode)) {
          const idx = nextState.search.resultsLookup.get(nextRovingNode)!;
          traceDispatch({
            type: 'set search iterator index',
            resultIndex: nextRovingTabIndex,
            resultIteratorIndex: idx,
          });
        } else if (nextState.search.resultIteratorIndex !== null) {
          traceDispatch({type: 'clear search iterator index'});
        }
      } else if (
        typeof nextSearchResultIndex === 'number' &&
        prevState.search.resultIndex !== nextSearchResultIndex &&
        action.type !== 'set search iterator index'
      ) {
        // If the search result index changes, mark the node as focused and scroll it into view
        const nextNode = props.tree.list[nextSearchResultIndex]!;
        setRowAsFocused(
          nextNode,
          null,
          nextState.search.resultsLookup,
          nextSearchResultIndex
        );
        scrollRowIntoView(nextNode, nextSearchResultIndex, 'center if outside');
      }
    };

    traceStateEmitter.on('before next state', beforeTraceNextStateDispatch);

    return () => {
      traceStateEmitter.off('before next state', beforeTraceNextStateDispatch);
    };
  }, [
    props.tree,
    onTraceSearch,
    traceStateEmitter,
    traceDispatch,
    setRowAsFocused,
    scrollRowIntoView,
  ]);

  const [traceGridRef, setTraceGridRef] = useState<HTMLElement | null>(null);

  // Memoized because it requires tree traversal
  const shape = useMemo(() => props.tree.shape, [props.tree]);

  useTraceTimelineChangeSync({
    tree: props.tree,
    traceScheduler,
  });

  useTraceSpaceListeners({
    view: traceView,
    viewManager,
    traceScheduler,
  });

  useDividerResizeSync(traceScheduler);

  const onLoadScrollStatus = useTraceOnLoad({
    onTraceLoad,
    pathToNodeOrEventId: scrollQueueRef.current,
    tree: props.tree,
    meta: props.meta,
  });

  // Sync part of the state with the URL
  const traceQueryStateSync = useMemo(() => {
    return {search: traceState.search.query};
  }, [traceState.search.query]);
  useTraceQueryParamStateSync(traceQueryStateSync);

  const onAutogroupChange = useCallback(() => {
    const value = !traceState.preferences.autogroup.parent;

    if (value) {
      let autogroupCount = 0;
      autogroupCount += TraceTree.AutogroupSiblingSpanNodes(props.tree.root);
      autogroupCount += TraceTree.AutogroupDirectChildrenSpanNodes(props.tree.root);
      addSuccessMessage(
        autogroupCount > 0
          ? tct('Autogrouping enabled, detected [count] autogrouping spans', {
              count: autogroupCount,
            })
          : t('Autogrouping enabled')
      );
    } else {
      let removeCount = 0;
      removeCount += TraceTree.RemoveSiblingAutogroupNodes(props.tree.root);
      removeCount += TraceTree.RemoveDirectChildrenAutogroupNodes(props.tree.root);

      addSuccessMessage(
        removeCount > 0
          ? tct('Autogrouping disabled, removed [count] autogroup spans', {
              count: removeCount,
            })
          : t('Autogrouping disabled')
      );
    }

    traceAnalytics.trackAutogroupingPreferenceChange(props.organization, value);
    props.tree.rebuild();
    traceDispatch({
      type: 'set autogrouping',
      payload: value,
    });
  }, [traceDispatch, traceState.preferences.autogroup, props.tree, props.organization]);

  const onMissingInstrumentationChange = useCallback(() => {
    const value = !traceState.preferences.missing_instrumentation;
    if (value) {
      const missingInstrumentationCount = TraceTree.DetectMissingInstrumentation(
        props.tree.root
      );
      addSuccessMessage(
        missingInstrumentationCount > 0
          ? tct(
              'Missing instrumentation enabled, found [count] missing instrumentation spans',
              {
                count: missingInstrumentationCount,
              }
            )
          : t('Missing instrumentation enabled')
      );
    } else {
      const removeCount = TraceTree.RemoveMissingInstrumentationNodes(props.tree.root);
      addSuccessMessage(
        removeCount > 0
          ? tct(
              'Missing instrumentation disabled, removed [count] missing instrumentation spans',
              {
                count: removeCount,
              }
            )
          : t('Missing instrumentation disabled')
      );
    }

    traceAnalytics.trackMissingInstrumentationPreferenceChange(props.organization, value);
    props.tree.rebuild();
    traceDispatch({
      type: 'set missing instrumentation',
      payload: value,
    });
  }, [
    traceDispatch,
    traceState.preferences.missing_instrumentation,
    props.tree,
    props.organization,
  ]);

  if (props.tree.type === 'empty' && props.hideIfNoData) {
    return null;
  }

  return (
    <Flex direction="column" flex={1}>
      <TraceTypeWarnings
        tree={props.tree}
        traceSlug={props.traceSlug}
        organization={organization}
      />
      <TraceToolbar>
        <TraceSearchInput onTraceSearch={onTraceSearch} organization={organization} />
        <TraceOpenInExploreButton
          trace_id={props.traceSlug}
          traceEventView={props.traceEventView}
        />
        <TraceResetZoomButton
          viewManager={viewManager}
          organization={props.organization}
        />
        <TracePreferencesDropdown
          rootEventResults={props.rootEventResults}
          autogroup={
            traceState.preferences.autogroup.parent &&
            traceState.preferences.autogroup.sibling
          }
          missingInstrumentation={traceState.preferences.missing_instrumentation}
          onAutogroupChange={onAutogroupChange}
          onMissingInstrumentationChange={onMissingInstrumentationChange}
        />
      </TraceToolbar>
      <TraceGrid layout={traceState.preferences.layout} ref={setTraceGridRef}>
        <DemoTourElement
          id={DemoTourStep.PERFORMANCE_SPAN_TREE}
          title={t('Trace Waterfall')}
          description={t(
            `Trace Waterfall offers a detailed look at traces for debugging slow services and errors.
            Each span represents a single operation or function call in the trace.
            Expanding a span will display sub-spans, and clicking on a span will display more details about the span.`
          )}
        >
          <Trace
            trace={props.tree}
            rerender={rerender}
            trace_id={props.traceSlug}
            onRowClick={onRowClick}
            onTraceSearch={onTraceSearch}
            previouslyFocusedNodeRef={previouslyFocusedNodeRef}
            manager={viewManager}
            scheduler={traceScheduler}
            forceRerender={forceRender}
            isLoading={props.tree.type === 'loading' || onLoadScrollStatus === 'pending'}
          />
        </DemoTourElement>

        {props.tree.type === 'loading' || onLoadScrollStatus === 'pending' ? (
          <TraceWaterfallState.Loading />
        ) : props.tree.type === 'error' ? (
          <TraceWaterfallState.Error />
        ) : props.tree.type === 'empty' ? (
          <TraceWaterfallState.Empty />
        ) : null}

        <TraceDrawer
          replay={props.replay}
          meta={props.meta}
          traceType={shape}
          trace={props.tree}
          traceId={props.traceSlug}
          traceGridRef={traceGridRef}
          manager={viewManager}
          scheduler={traceScheduler}
          onTabScrollToNode={onTabScrollToNode}
          onScrollToNode={onScrollToNode}
          traceEventView={props.traceEventView}
        />
      </TraceGrid>
      {showLinkedTraces && !isTraceItemDetailsResponse(props.rootEventResults.data) && (
        <TraceLinksNavigationContainer>
          <TraceLinkNavigationButton
            direction={'previous'}
            isLoading={props.rootEventResults.isLoading}
            traceContext={props.rootEventResults.data?.contexts.trace}
            currentTraceTimestamps={{
              start: props.rootEventResults.data?.startTimestamp,
              end: props.rootEventResults.data?.endTimestamp,
            }}
          />
          <TraceLinkNavigationButton
            direction={'next'}
            isLoading={props.rootEventResults.isLoading}
            projectID={props.rootEventResults.data?.projectID ?? ''}
            traceContext={props.rootEventResults.data?.contexts.trace}
            currentTraceTimestamps={{
              start: props.rootEventResults.data?.startTimestamp,
              end: props.rootEventResults.data?.endTimestamp,
            }}
          />
        </TraceLinksNavigationContainer>
      )}
    </Flex>
  );
}

const TraceToolbar = styled('div')`
  display: flex;
  gap: ${space(1)};
`;

const TraceLinksNavigationContainer = styled('div')`
  display: flex;
  justify-content: space-between;
  flex-direction: row;

  &:not(:empty) {
    margin-top: ${space(1)};
  }
`;

export const TraceGrid = styled('div')<{
  layout: 'drawer bottom' | 'drawer left' | 'drawer right';
}>`
  ${traceGridCssVariables}

  background-color: ${p => p.theme.background};
  border: 1px solid ${p => p.theme.border};
  flex: 1 1 100%;
  display: grid;
  overflow: hidden;
  position: relative;

  /* false positive for grid layout */
  /* stylelint-disable */
  grid-template-areas: ${p =>
    p.layout === 'drawer bottom'
      ? `
      'trace'
      'drawer'
      `
      : p.layout === 'drawer left'
        ? `'drawer trace'`
        : `'trace drawer'`};
  grid-template-columns: ${p =>
    p.layout === 'drawer bottom'
      ? '1fr'
      : p.layout === 'drawer left'
        ? 'min-content 1fr'
        : '1fr min-content'};
  grid-template-rows: 1fr auto;

  ${p => `border-radius: ${p.theme.borderRadius};`}
`;
