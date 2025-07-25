import {Fragment} from 'react';
import styled from '@emotion/styled';

import * as Layout from 'sentry/components/layouts/thirds';
import LoadingError from 'sentry/components/loadingError';
import LoadingIndicator from 'sentry/components/loadingIndicator';
import NoProjectMessage from 'sentry/components/noProjectMessage';
import SentryDocumentTitle from 'sentry/components/sentryDocumentTitle';
import {t} from 'sentry/locale';
import type {RouteComponentProps} from 'sentry/types/legacyReactRouter';
import type {TeamWithProjects} from 'sentry/types/project';
import localStorage from 'sentry/utils/localStorage';
import useRouteAnalyticsEventNames from 'sentry/utils/routeAnalytics/useRouteAnalyticsEventNames';
import useOrganization from 'sentry/utils/useOrganization';
import {useUserTeams} from 'sentry/utils/useUserTeams';
import {usePrefersStackedNav} from 'sentry/views/nav/usePrefersStackedNav';
import Header from 'sentry/views/organizationStats/header';

import TeamStatsControls from './controls';
import DescriptionCard from './descriptionCard';
import TeamAlertsTriggered from './teamAlertsTriggered';
import TeamMisery from './teamMisery';
import TeamReleases from './teamReleases';
import TeamStability from './teamStability';
import {dataDatetime} from './utils';

type Props = RouteComponentProps;

function TeamStatsHealth({location, router}: Props) {
  const organization = useOrganization();
  const {teams, isLoading, isError} = useUserTeams();
  const prefersStackedNav = usePrefersStackedNav();

  useRouteAnalyticsEventNames('team_insights.viewed', 'Team Insights: Viewed');

  const query = location?.query ?? {};
  const localStorageKey = `teamInsightsSelectedTeamId:${organization.slug}`;

  let localTeamId: string | null | undefined =
    query.team ?? localStorage.getItem(localStorageKey);
  if (localTeamId && !teams.some(team => team.id === localTeamId)) {
    localTeamId = null;
  }
  const currentTeamId = localTeamId ?? teams[0]?.id;
  const currentTeam = teams.find(team => team.id === currentTeamId) as
    | TeamWithProjects
    | undefined;
  const projects = currentTeam?.projects ?? [];

  const {period, start, end, utc} = dataDatetime(query);

  if (teams.length === 0) {
    return (
      <NoProjectMessage organization={organization} superuserNeedsToBeProjectMember />
    );
  }

  if (isError) {
    return <LoadingError />;
  }

  const BodyWrapper = prefersStackedNav ? NewLayoutBody : Body;

  return (
    <Fragment>
      <SentryDocumentTitle title={t('Project Health')} orgSlug={organization.slug} />
      <Header organization={organization} activeTab="health" />

      <BodyWrapper>
        <TeamStatsControls
          location={location}
          router={router}
          currentTeam={currentTeam}
        />

        {isLoading && <LoadingIndicator />}
        {!isLoading && (
          <Layout.Main fullWidth>
            <DescriptionCard
              title={t('Crash Free Sessions')}
              description={t(
                'The percentage of healthy, errored, and abnormal sessions that didn’t cause a crash.'
              )}
            >
              <TeamStability
                projects={projects}
                organization={organization}
                period={period}
                start={start}
                end={end}
                utc={utc}
              />
            </DescriptionCard>

            <DescriptionCard
              title={t('User Misery')}
              description={t(
                'The number of unique users that experienced load times 4x the project’s configured threshold.'
              )}
            >
              <TeamMisery
                organization={organization}
                projects={projects}
                teamId={currentTeam!.id}
                period={period}
                start={start?.toString()}
                end={end?.toString()}
                location={location}
              />
            </DescriptionCard>

            <DescriptionCard
              title={t('Metric Alerts Triggered')}
              description={t('Alerts triggered from the Alert Rules your team created.')}
            >
              <TeamAlertsTriggered
                organization={organization}
                projects={projects}
                teamSlug={currentTeam!.slug}
                period={period}
                start={start?.toString()}
                end={end?.toString()}
              />
            </DescriptionCard>

            <DescriptionCard
              title={t('Number of Releases')}
              description={t('The releases that were created in your team’s projects.')}
            >
              <TeamReleases
                projects={projects}
                organization={organization}
                teamSlug={currentTeam!.slug}
                period={period}
                start={start}
                end={end}
                utc={utc}
              />
            </DescriptionCard>
          </Layout.Main>
        )}
      </BodyWrapper>
    </Fragment>
  );
}

export default TeamStatsHealth;

const Body = styled(Layout.Body)`
  @media (min-width: ${p => p.theme.breakpoints.md}) {
    display: block;
  }
`;

const NewLayoutBody = styled('div')``;
