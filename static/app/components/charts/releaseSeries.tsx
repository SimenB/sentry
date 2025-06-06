import {Component} from 'react';
import type {Theme} from '@emotion/react';
import {withTheme} from '@emotion/react';
import type {Query} from 'history';
import isEqual from 'lodash/isEqual';
import memoize from 'lodash/memoize';
import partition from 'lodash/partition';

import {addErrorMessage} from 'sentry/actionCreators/indicator';
import type {Client, ResponseMeta} from 'sentry/api';
import MarkLine from 'sentry/components/charts/components/markLine';
import {t} from 'sentry/locale';
import type {DateString} from 'sentry/types/core';
import type {Series} from 'sentry/types/echarts';
import type {WithRouterProps} from 'sentry/types/legacyReactRouter';
import type {Organization} from 'sentry/types/organization';
import {escape} from 'sentry/utils';
import {getFormat, getFormattedDate, getUtcDateString} from 'sentry/utils/dates';
import parseLinkHeader from 'sentry/utils/parseLinkHeader';
import {formatVersion} from 'sentry/utils/versions/formatVersion';
import withApi from 'sentry/utils/withApi';
import withOrganization from 'sentry/utils/withOrganization';
// eslint-disable-next-line no-restricted-imports
import withSentryRouter from 'sentry/utils/withSentryRouter';
import {makeReleasesPathname} from 'sentry/views/releases/utils/pathnames';

type ReleaseMetaBasic = {
  date: string;
  version: string;
};

type ReleaseConditions = {
  end: DateString;
  environment: readonly string[];
  project: readonly number[];
  start: DateString;
  cursor?: string;
  query?: string;
  statsPeriod?: string | null;
};

// This is not an exported action/function because releases list uses AsyncComponent
// and this is not re-used anywhere else afaict
function getOrganizationReleases(
  api: Client,
  organization: Organization,
  conditions: ReleaseConditions
) {
  const query: Record<string, string> = {};
  Object.keys(conditions).forEach(key => {
    let value = (conditions as any)[key];
    if (value && (key === 'start' || key === 'end')) {
      value = getUtcDateString(value);
    }
    if (value) {
      query[key] = value;
    }
  });
  api.clear();
  return api.requestPromise(`/organizations/${organization.slug}/releases/stats/`, {
    includeAllArgs: true,
    method: 'GET',
    query,
  }) as Promise<[ReleaseMetaBasic[], any, ResponseMeta]>;
}

const getOrganizationReleasesMemoized = memoize(
  getOrganizationReleases,
  (_, __, conditions) =>
    Object.values(conditions)
      .map(val => JSON.stringify(val))
      .join('-')
);

export interface ReleaseSeriesProps extends WithRouterProps {
  api: Client;
  children: (s: State) => React.ReactNode;
  end: DateString;
  environments: readonly string[];
  organization: Organization;
  projects: readonly number[];
  start: DateString;
  theme: Theme;
  emphasizeReleases?: string[];
  enabled?: boolean;
  memoized?: boolean;
  period?: string | null;
  preserveQueryParams?: boolean;
  query?: string;
  queryExtra?: Query;
  releases?: ReleaseMetaBasic[] | null;
  tooltip?: Exclude<Parameters<typeof MarkLine>[0], undefined>['tooltip'];
  utc?: boolean | null;
}

type State = {
  releaseSeries: Series[];
  releases: ReleaseMetaBasic[] | null;
};

class ReleaseSeries extends Component<ReleaseSeriesProps, State> {
  state: State = {
    releases: null,
    releaseSeries: [],
  };

  componentDidMount() {
    this._isMounted = true;
    const {releases, enabled = true} = this.props;

    if (releases) {
      // No need to fetch releases if passed in from props
      this.setReleasesWithSeries(releases);
      return;
    }

    if (enabled) {
      this.fetchData();
    }
  }

  componentDidUpdate(prevProps: any) {
    const {enabled = true} = this.props;

    if (
      (!isEqual(prevProps.projects, this.props.projects) ||
        !isEqual(prevProps.environments, this.props.environments) ||
        !isEqual(prevProps.start, this.props.start) ||
        !isEqual(prevProps.end, this.props.end) ||
        !isEqual(prevProps.period, this.props.period) ||
        !isEqual(prevProps.query, this.props.query) ||
        (!prevProps.enabled && this.props.enabled)) &&
      enabled
    ) {
      this.fetchData();
    } else if (!isEqual(prevProps.emphasizeReleases, this.props.emphasizeReleases)) {
      this.setReleasesWithSeries(this.state.releases);
    }
  }

  componentWillUnmount() {
    this._isMounted = false;
    this.props.api.clear();
  }

  _isMounted = false;

  async fetchData() {
    const {
      api,
      organization,
      projects,
      environments,
      period,
      start,
      end,
      memoized,
      query,
    } = this.props;
    const conditions: ReleaseConditions = {
      start,
      end,
      project: projects,
      environment: environments,
      statsPeriod: period,
      query,
    };
    let hasMore = true;
    const releases: ReleaseMetaBasic[] = [];
    while (hasMore) {
      try {
        const getReleases = memoized
          ? getOrganizationReleasesMemoized
          : getOrganizationReleases;
        const [newReleases, , resp] = await getReleases(api, organization, conditions);
        releases.push(...newReleases);
        if (this._isMounted) {
          this.setReleasesWithSeries(releases);
        }

        const pageLinks = resp?.getResponseHeader('Link');
        if (pageLinks) {
          const paginationObject = parseLinkHeader(pageLinks);
          hasMore = paginationObject?.next?.results ?? false;
          conditions.cursor = paginationObject.next!.cursor;
        } else {
          hasMore = false;
        }
      } catch {
        addErrorMessage(t('Error fetching releases'));
        hasMore = false;
      }
    }
  }

  setReleasesWithSeries(releases: any) {
    const {emphasizeReleases = []} = this.props;
    const releaseSeries: Series[] = [];

    if (emphasizeReleases.length) {
      const [unemphasizedReleases, emphasizedReleases] = partition(
        releases,
        release => !emphasizeReleases.includes(release.version)
      );
      if (unemphasizedReleases.length) {
        releaseSeries.push(this.getReleaseSeries(unemphasizedReleases, {type: 'dotted'}));
      }
      if (emphasizedReleases.length) {
        releaseSeries.push(
          this.getReleaseSeries(emphasizedReleases, {
            opacity: 0.8,
          })
        );
      }
    } else {
      releaseSeries.push(this.getReleaseSeries(releases));
    }

    this.setState({
      releases,
      releaseSeries,
    });
  }

  getReleaseSeries = (releases: any, lineStyle = {}) => {
    const {
      organization,
      router,
      tooltip,
      environments,
      start,
      end,
      period,
      preserveQueryParams,
      queryExtra,
      theme,
    } = this.props;

    const query = {...queryExtra};
    if (organization.features.includes('global-views')) {
      query.project = router.location.query.project;
    }
    if (preserveQueryParams) {
      query.environment = [...environments];
      query.start = start ? getUtcDateString(start) : undefined;
      query.end = end ? getUtcDateString(end) : undefined;
      query.statsPeriod = period || undefined;
    }

    const markLine = MarkLine({
      animation: false,
      lineStyle: {
        color: theme.purple300,
        opacity: 0.3,
        type: 'solid',
        ...lineStyle,
      },
      label: {
        show: false,
      },
      data: releases.map((release: any) => ({
        xAxis: +new Date(release.date),
        name: formatVersion(release.version, true),
        value: formatVersion(release.version, true),

        onClick: () => {
          router.push({
            pathname: makeReleasesPathname({
              organization,
              path: `/${encodeURIComponent(release.version)}/`,
            }),
            query,
          });
        },

        label: {
          formatter: () => formatVersion(release.version, true),
        },
      })),
      tooltip: tooltip || {
        trigger: 'item',
        formatter: ({data}: any) => {
          // Should only happen when navigating pages
          if (!data) {
            return '';
          }
          // XXX using this.props here as this function does not get re-run
          // unless projects are changed. Using a closure variable would result
          // in stale values.
          const time = getFormattedDate(
            data.value,
            getFormat({timeZone: true, year: true}),
            {
              local: !this.props.utc,
            }
          );
          const version = escape(formatVersion(data.name, true));
          return [
            '<div class="tooltip-series">',
            `<div><span class="tooltip-label"><strong>${t(
              'Release'
            )}</strong></span> ${version}</div>`,
            '</div>',
            '<div class="tooltip-footer">',
            time,
            '</div>',
            '<div class="tooltip-arrow"></div>',
          ].join('');
        },
      },
    });

    return {
      id: 'release-lines',
      seriesName: 'Releases',
      color: theme.purple200,
      data: [],
      markLine,
    };
  };

  render() {
    const {children, enabled = true} = this.props;

    return children({
      releases: enabled ? this.state.releases : [],
      releaseSeries: enabled ? this.state.releaseSeries : [],
    });
  }
}

export default withSentryRouter(withOrganization(withApi(withTheme(ReleaseSeries))));
