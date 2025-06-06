import {t} from 'sentry/locale';
import type {Organization} from 'sentry/types/organization';
import {prefersStackedNav} from 'sentry/views/nav/prefersStackedNav';
import {getUserOrgNavigationConfiguration} from 'sentry/views/settings/organization/userOrgNavigationConfiguration';
import type {NavigationSection} from 'sentry/views/settings/types';

const pathPrefix = '/settings/account';

type ConfigParams = {
  organization?: Organization;
};

function getConfiguration({organization}: ConfigParams): NavigationSection[] {
  if (organization && prefersStackedNav(organization)) {
    return getUserOrgNavigationConfiguration();
  }

  return [
    {
      name: t('Account'),
      id: 'settings-account',
      items: [
        {
          path: `${pathPrefix}/details/`,
          title: t('Account Details'),
          description: t(
            'Change your account details and preferences (e.g. timezone/clock, avatar, language)'
          ),
        },
        {
          path: `${pathPrefix}/security/`,
          title: t('Security'),
          description: t('Change your account password and/or two factor authentication'),
        },
        {
          path: `${pathPrefix}/notifications/`,
          title: t('Notifications'),
          description: t('Configure what email notifications to receive'),
        },
        {
          path: `${pathPrefix}/emails/`,
          title: t('Email Addresses'),
          description: t(
            'Add or remove secondary emails, change your primary email, verify your emails'
          ),
        },
        {
          path: `${pathPrefix}/subscriptions/`,
          title: t('Subscriptions'),
          description: t(
            'Change Sentry marketing subscriptions you are subscribed to (GDPR)'
          ),
        },
        {
          path: `${pathPrefix}/authorizations/`,
          title: t('Authorized Applications'),
          description: t(
            'Manage third-party applications that have access to your Sentry account'
          ),
        },
        {
          path: `${pathPrefix}/identities/`,
          title: t('Identities'),
          description: t(
            'Manage your third-party identities that are associated to Sentry'
          ),
        },
        {
          path: `${pathPrefix}/close-account/`,
          title: t('Close Account'),
          description: t('Permanently close your Sentry account'),
        },
      ],
    },
    {
      id: 'settings-api',
      name: t('API'),
      items: [
        {
          path: `${pathPrefix}/api/applications/`,
          title: t('Applications'),
          description: t('Add and configure OAuth2 applications'),
        },
        {
          path: `${pathPrefix}/api/auth-tokens/`,
          title: t('Personal Tokens'),
          description: t(
            "Personal tokens allow you to perform actions against the Sentry API on behalf of your account. They're the easiest way to get started using the API."
          ),
        },
      ],
    },
  ];
}

export default getConfiguration;
