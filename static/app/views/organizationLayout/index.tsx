import {ScrollRestoration} from 'react-router-dom';
import styled from '@emotion/styled';

import DemoHeader from 'sentry/components/demo/demoHeader';
import {useFeatureFlagOnboardingDrawer} from 'sentry/components/events/featureFlags/onboarding/featureFlagOnboardingSidebar';
import {useFeedbackOnboardingDrawer} from 'sentry/components/feedback/feedbackOnboarding/sidebar';
import Footer from 'sentry/components/footer';
import {GlobalDrawer} from 'sentry/components/globalDrawer';
import HookOrDefault from 'sentry/components/hookOrDefault';
import {usePerformanceOnboardingDrawer} from 'sentry/components/performanceOnboarding/sidebar';
import {useProfilingOnboardingDrawer} from 'sentry/components/profiling/profilingOnboardingSidebar';
import {useReplaysOnboardingDrawer} from 'sentry/components/replaysOnboarding/sidebar';
import SentryDocumentTitle from 'sentry/components/sentryDocumentTitle';
import Sidebar from 'sentry/components/sidebar';
import type {Organization} from 'sentry/types/organization';
import useRouteAnalyticsHookSetup from 'sentry/utils/routeAnalytics/useRouteAnalyticsHookSetup';
import useRouteAnalyticsParams from 'sentry/utils/routeAnalytics/useRouteAnalyticsParams';
import useDevToolbar from 'sentry/utils/useDevToolbar';
import {useIsSentryEmployee} from 'sentry/utils/useIsSentryEmployee';
import useOrganization from 'sentry/utils/useOrganization';
import {AppBodyContent} from 'sentry/views/app/appBodyContent';
import Nav from 'sentry/views/nav';
import {NavContextProvider} from 'sentry/views/nav/context';
import {usePrefersStackedNav} from 'sentry/views/nav/usePrefersStackedNav';
import OrganizationContainer from 'sentry/views/organizationContainer';
import {useReleasesDrawer} from 'sentry/views/releases/drawer/useReleasesDrawer';

import OrganizationDetailsBody from './body';

interface Props {
  children: React.ReactNode;
}

const OrganizationHeader = HookOrDefault({
  hookName: 'component:organization-header',
});

function DevToolInit() {
  const isEmployee = useIsSentryEmployee();
  const organization = useOrganization();
  const showDevToolbar = organization.features.includes('devtoolbar');
  useDevToolbar({enabled: showDevToolbar && isEmployee});
  return null;
}

function OrganizationLayout({children}: Props) {
  useRouteAnalyticsHookSetup();

  // XXX(epurkhiser): The OrganizationContainer is responsible for ensuring the
  // oganization is loaded before rendering children. Organization may not be
  // loaded yet when this first renders.
  const organization = useOrganization({allowNull: true});
  const prefersStackedNav = usePrefersStackedNav();
  const App = prefersStackedNav ? AppLayout : LegacyAppLayout;

  useRouteAnalyticsParams({
    prefers_stacked_navigation: prefersStackedNav,
  });

  return (
    <SentryDocumentTitle noSuffix title={organization?.name ?? 'Sentry'}>
      <OrganizationContainer>
        <GlobalDrawer>
          <App organization={organization}>{children}</App>
        </GlobalDrawer>
      </OrganizationContainer>
      <ScrollRestoration getKey={location => location.pathname} />
    </SentryDocumentTitle>
  );
}

interface LayoutProps extends Props {
  organization: Organization | null;
}

function AppDrawers() {
  useFeedbackOnboardingDrawer();
  useReplaysOnboardingDrawer();
  usePerformanceOnboardingDrawer();
  useProfilingOnboardingDrawer();
  useFeatureFlagOnboardingDrawer();
  useReleasesDrawer();

  return null;
}

function AppLayout({children, organization}: LayoutProps) {
  return (
    <NavContextProvider>
      <AppContainer>
        <Nav />
        {/* The `#main` selector is used to make the app content `inert` when an overlay is active */}
        <BodyContainer id="main">
          <AppBodyContent>
            {organization && <OrganizationHeader organization={organization} />}
            {organization && <DevToolInit />}
            <OrganizationDetailsBody>{children}</OrganizationDetailsBody>
          </AppBodyContent>
          <Footer />
        </BodyContainer>
      </AppContainer>
      {organization ? <AppDrawers /> : null}
    </NavContextProvider>
  );
}

function LegacyAppLayout({children, organization}: LayoutProps) {
  useReleasesDrawer();

  return (
    <div className="app">
      <DemoHeader />
      {organization && <OrganizationHeader organization={organization} />}
      {organization && <DevToolInit />}
      <Sidebar />
      <AppBodyContent>
        <OrganizationDetailsBody>{children}</OrganizationDetailsBody>
      </AppBodyContent>
      <Footer />
    </div>
  );
}

const AppContainer = styled('div')`
  position: relative;
  display: flex;
  flex-direction: column;
  flex-grow: 1;

  @media (min-width: ${p => p.theme.breakpoints.medium}) {
    flex-direction: row;
  }
`;

const BodyContainer = styled('div')`
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
`;

export default OrganizationLayout;
