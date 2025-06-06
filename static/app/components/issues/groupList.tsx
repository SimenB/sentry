import {Component, Fragment} from 'react';
import styled from '@emotion/styled';
import isEqual from 'lodash/isEqual';
import omit from 'lodash/omit';
import * as qs from 'query-string';

import {fetchOrgMembers, indexMembersByProject} from 'sentry/actionCreators/members';
import type {Client} from 'sentry/api';
import EmptyStateWarning from 'sentry/components/emptyStateWarning';
import LoadingError from 'sentry/components/loadingError';
import Pagination from 'sentry/components/pagination';
import Panel from 'sentry/components/panels/panel';
import PanelBody from 'sentry/components/panels/panelBody';
import Placeholder from 'sentry/components/placeholder';
import {parseSearch, Token} from 'sentry/components/searchSyntax/parser';
import {treeResultLocator} from 'sentry/components/searchSyntax/utils';
import StreamGroup, {
  DEFAULT_STREAM_GROUP_STATS_PERIOD,
} from 'sentry/components/stream/group';
import {t} from 'sentry/locale';
import GroupStore from 'sentry/stores/groupStore';
import {space} from 'sentry/styles/space';
import type {Group} from 'sentry/types/group';
import type {WithRouterProps} from 'sentry/types/legacyReactRouter';
import type {Organization} from 'sentry/types/organization';
import withApi from 'sentry/utils/withApi';
import withOrganization from 'sentry/utils/withOrganization';
// eslint-disable-next-line no-restricted-imports
import withSentryRouter from 'sentry/utils/withSentryRouter';
import type {TimePeriodType} from 'sentry/views/alerts/rules/metric/details/constants';
import {RELATED_ISSUES_BOOLEAN_QUERY_ERROR} from 'sentry/views/alerts/rules/metric/details/relatedIssuesNotAvailable';

import GroupListHeader from './groupListHeader';

const defaultProps = {
  canSelectGroups: true,
  withChart: true,
  withPagination: true,
  useFilteredStats: true,
  useTintRow: true,
};

export type GroupListColumn =
  | 'graph'
  | 'event'
  | 'users'
  | 'priority'
  | 'assignee'
  | 'lastTriggered'
  | 'firstSeen'
  | 'lastSeen';

type Props = WithRouterProps & {
  api: Client;
  organization: Organization;
  queryParams: Record<string, number | string | string[] | undefined | null>;
  customStatsPeriod?: TimePeriodType;
  /**
   * Defaults to `/organizations/${orgSlug}/issues/`
   */
  endpointPath?: string;
  onFetchSuccess?: (
    groupListState: State,
    onCursor: (
      cursor: string,
      path: string,
      query: Record<string, any>,
      pageDiff: number
    ) => void
  ) => void;
  /**
   * Use `query` within `queryParams` for passing the parameter to the endpoint
   */
  query?: string;
  queryFilterDescription?: string;
  renderEmptyMessage?: () => React.ReactNode;
  renderErrorMessage?: (props: {detail: string}, retry: () => void) => React.ReactNode;
  // where the group list is rendered
  source?: string;
  withColumns?: GroupListColumn[];
} & Partial<typeof defaultProps>;

type State = {
  error: boolean;
  errorData: {detail: string} | null;
  groups: Group[];
  loading: boolean;
  pageLinks: string | null;
  memberList?: ReturnType<typeof indexMembersByProject>;
};

class GroupList extends Component<Props, State> {
  static defaultProps = defaultProps;

  state: State = {
    loading: true,
    error: false,
    errorData: null,
    groups: [],
    pageLinks: null,
  };

  componentDidMount() {
    this.fetchData();
  }

  shouldComponentUpdate(nextProps: Props, nextState: State) {
    return (
      !isEqual(this.state, nextState) ||
      nextProps.endpointPath !== this.props.endpointPath ||
      nextProps.query !== this.props.query ||
      !isEqual(nextProps.queryParams, this.props.queryParams)
    );
  }

  componentDidUpdate(prevProps: Props) {
    const ignoredQueryParams = ['end'];

    if (
      prevProps.organization.slug !== this.props.organization.slug ||
      prevProps.endpointPath !== this.props.endpointPath ||
      prevProps.query !== this.props.query ||
      !isEqual(
        omit(prevProps.queryParams, ignoredQueryParams),
        omit(this.props.queryParams, ignoredQueryParams)
      )
    ) {
      this.fetchData();
    }
  }

  componentWillUnmount() {
    GroupStore.reset();
    this.listener?.();
  }

  listener = GroupStore.listen(() => this.onGroupChange(), undefined);

  fetchData = async () => {
    GroupStore.loadInitialData([]);
    const {api, organization, queryParams} = this.props;
    api.clear();

    this.setState({loading: true, error: false, errorData: null});

    fetchOrgMembers(api, organization.slug).then(members => {
      this.setState({memberList: indexMembersByProject(members)});
    });

    const endpoint = this.getGroupListEndpoint();

    const parsedQuery = parseSearch(
      (queryParams ?? this.getQueryParams()).query as string
    );
    const hasLogicBoolean = parsedQuery
      ? treeResultLocator<boolean>({
          tree: parsedQuery,
          noResultValue: false,
          visitorTest: ({token, returnResult}) => {
            return token.type === Token.LOGIC_BOOLEAN ? returnResult(true) : null;
          },
        })
      : false;

    // Check if the alert rule query has AND or OR
    // logic queries haven't been implemented for issue search yet
    if (hasLogicBoolean) {
      this.setState({
        error: true,
        errorData: {detail: RELATED_ISSUES_BOOLEAN_QUERY_ERROR},
        loading: false,
      });
      return;
    }

    try {
      const [data, , jqXHR] = await api.requestPromise(endpoint, {
        includeAllArgs: true,
      });

      GroupStore.add(data);

      this.setState(
        {
          error: false,
          errorData: null,
          loading: false,
          pageLinks: jqXHR?.getResponseHeader('Link') ?? null,
        },
        () => {
          this.props.onFetchSuccess?.(this.state, this.handleCursorChange);
        }
      );
    } catch (error) {
      this.setState({error: true, errorData: error.responseJSON, loading: false});
    }
  };

  getGroupListEndpoint() {
    // TODO: Split up the query parameters and the URL. This will make it much easier to mock the endpoint.
    const {organization, endpointPath, queryParams} = this.props;
    const path = endpointPath ?? `/organizations/${organization.slug}/issues/`;
    const queryParameters = queryParams ?? this.getQueryParams();

    return `${path}?${qs.stringify(queryParameters)}`;
  }

  getQueryParams() {
    const {location, query} = this.props;

    const queryParams = location.query;
    queryParams.limit = 50;
    queryParams.sort = 'new';
    queryParams.query = query;

    return queryParams;
  }

  handleCursorChange = (
    cursor: string | undefined,
    path: string,
    query: Record<string, any>,
    pageDiff: number
  ) => {
    const queryPageInt = parseInt(query.page, 10);
    let nextPage: number | undefined = isNaN(queryPageInt)
      ? pageDiff
      : queryPageInt + pageDiff;

    // unset cursor and page when we navigate back to the first page
    // also reset cursor if somehow the previous button is enabled on
    // first page and user attempts to go backwards
    if (nextPage <= 0) {
      cursor = undefined;
      nextPage = undefined;
    }

    this.props.router.push({
      pathname: path,
      query: {...query, cursor, page: nextPage},
    });
  };

  onGroupChange() {
    const groups = GroupStore.getAllItems() as Group[];
    if (!isEqual(groups, this.state.groups)) {
      this.setState({groups});
    }
  }

  render() {
    const {
      canSelectGroups,
      withChart,
      withColumns = ['graph', 'event', 'users', 'assignee'],
      renderEmptyMessage,
      renderErrorMessage,
      withPagination,
      useFilteredStats,
      useTintRow,
      customStatsPeriod,
      queryParams,
      queryFilterDescription,
      source,
      query,
    } = this.props;
    const {loading, error, errorData, groups, memberList, pageLinks} = this.state;

    const columns: GroupListColumn[] = [
      ...withColumns,
      'firstSeen' as const,
      'lastSeen' as const,
    ];

    if (error) {
      if (typeof renderErrorMessage === 'function' && errorData) {
        return renderErrorMessage(errorData, this.fetchData);
      }

      return <LoadingError onRetry={this.fetchData} />;
    }

    if (!loading && groups.length === 0) {
      if (typeof renderEmptyMessage === 'function') {
        return renderEmptyMessage();
      }
      return (
        <Panel>
          <PanelBody>
            <EmptyStateWarning>
              <p>{t("There don't seem to be any events fitting the query.")}</p>
            </EmptyStateWarning>
          </PanelBody>
        </Panel>
      );
    }

    const statsPeriod =
      queryParams?.groupStatsPeriod === 'auto'
        ? queryParams?.groupStatsPeriod
        : DEFAULT_STREAM_GROUP_STATS_PERIOD;

    return (
      <Fragment>
        <PanelContainer>
          <GroupListHeader withChart={!!withChart} withColumns={columns} />
          <PanelBody>
            {loading
              ? [
                  ...new Array(
                    typeof queryParams?.limit === 'number' ? queryParams?.limit : 4
                  ),
                ].map((_, i) => (
                  <GroupPlaceholder key={i}>
                    <Placeholder height="50px" />
                  </GroupPlaceholder>
                ))
              : groups.map(({id, project}) => {
                  const members = memberList?.hasOwnProperty(project.slug)
                    ? memberList[project.slug]
                    : undefined;

                  return (
                    <StreamGroup
                      key={id}
                      id={id}
                      canSelect={canSelectGroups}
                      withChart={withChart}
                      withColumns={columns}
                      memberList={members}
                      useFilteredStats={useFilteredStats}
                      useTintRow={useTintRow}
                      customStatsPeriod={customStatsPeriod}
                      statsPeriod={statsPeriod}
                      queryFilterDescription={queryFilterDescription}
                      source={source}
                      query={query}
                    />
                  );
                })}
          </PanelBody>
        </PanelContainer>
        {withPagination && (
          <Pagination pageLinks={pageLinks} onCursor={this.handleCursorChange} />
        )}
      </Fragment>
    );
  }
}

export default withOrganization(withApi(withSentryRouter(GroupList)));

const GroupPlaceholder = styled('div')`
  padding: ${space(1)};

  &:not(:last-child) {
    border-bottom: solid 1px ${p => p.theme.innerBorder};
  }
`;

const PanelContainer = styled(Panel)`
  container-type: inline-size;
`;
