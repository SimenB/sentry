import type {
  Integration,
  IntegrationProvider,
  Plugin,
  SentryApp,
} from 'sentry/types/integrations';

export function ProviderListFixture(): {providers: IntegrationProvider[]} {
  return {
    providers: [
      {
        canAdd: true,
        canDisable: false,
        features: ['commits', 'issue-basic'],
        key: 'bitbucket',

        metadata: {
          aspects: {},
          author: 'The Sentry Team',
          description:
            'Connect your Sentry organization to Bitbucket, enabling the following features:',

          features: [],
          issue_url:
            'https://github.com/getsentry/sentry/issues/new?template=bug.yml&title=Bitbucket%20Integration:%20&labels=Component%3A%20Integrations',
          noun: 'Installation',
          source_url:
            'https://github.com/getsentry/sentry/tree/master/src/sentry/integrations/bitbucket',
        },
        name: 'Bitbucket',

        setupDialog: {
          height: 600,
          url: '/organizations/sentry/integrations/bitbucket/setup/',
          width: 600,
        },
        slug: 'bitbucket',
      },
    ],
  };
}

export function BitbucketIntegrationConfigFixture(): Integration {
  return {
    accountType: '',
    gracePeriodEnd: '',
    organizationIntegrationStatus: 'active',
    domainName: 'bitbucket.org/%7Bfb715533-bbd7-4666-aa57-01dc93dd9cc0%7D',
    icon: 'https://secure.gravatar.com/avatar/8b4cb68e40b74c90427d8262256bd1c8?d=https%3A%2F%2Favatar-management--avatars.us-west-2.prod.public.atl-paas.net%2Finitials%2FNN-0.png',
    id: '4',
    name: '{fb715533-bbd7-4666-aa57-01dc93dd9cc0}',
    provider: {
      aspects: {},
      canAdd: true,
      canDisable: false,
      features: ['commits', 'issue-basic'],
      key: 'bitbucket',
      name: 'Bitbucket',
      slug: 'bitbucket',
    },
    status: 'active',
  };
}

export function GitHubIntegrationConfigFixture(): Integration {
  return {
    accountType: '',
    gracePeriodEnd: '',
    organizationIntegrationStatus: 'active',
    domainName: 'github.com',
    icon: 'https://secure.gravatar.com/avatar/8b4cb68e40b74c90427d8262256bd1c8',
    id: '5',
    name: 'NisanthanNanthakumar',
    provider: {
      aspects: {},
      canAdd: true,
      canDisable: false,
      features: ['commits', 'issue-basic'],
      key: 'github',
      name: 'Github',
      slug: 'github',
    },
    status: 'active',
  };
}

export function OrgOwnedAppsFixture(): SentryApp[] {
  return [
    {
      author: 'Sentry',
      clientId: 'a6d35972d4164ef18845b1e2ca954fe70ac196e0b20d4d1e8760a38772cf6f1c',
      clientSecret: '8f47dcef40f7486f9bacfeca257022e092a483add7cf4d619993b9ace9775a79',
      events: [],
      isAlertable: false,
      name: 'My Headband Washer',
      overview: null,
      owner: {id: 1, slug: 'sentry'},
      redirectUrl: null,
      schema: {},
      scopes: ['project:read', 'team:read', 'team:write'],
      slug: 'my-headband-washer-289499',
      status: 'internal',
      uuid: 'a806ab10-9608-4a4f-8dd9-ca6d6c09f9f5',
      verifyInstall: false,
      webhookUrl: 'https://myheadbandwasher.com',
      featureData: [],
      popularity: null,
    },
    {
      author: 'La Croix',
      clientId: '8cc36458a0f94c93816e06dce7d808f882cbef59af6040d2b9ec4d67092c80f1',
      clientSecret: '2b2aeb743c3745ab832e03bf02a7d91851908d379646499f900cd115780e8b2b',
      events: [],
      isAlertable: false,
      name: 'La Croix Monitor',
      overview: null,

      owner: {id: 1, slug: 'sentry'},
      redirectUrl: null,
      schema: {},

      scopes: ['project:read', 'project:write', 'team:read'],
      slug: 'la-croix-monitor',
      status: 'unpublished',
      uuid: 'a59c8fcc-2f27-49f8-af9e-02661fc3e8d7',
      verifyInstall: false,
      webhookUrl: 'https://lacroix.com',
      featureData: [
        {
          description:
            'La Croix can **utilize the Sentry API** to pull data or update resources in Sentry (with permissions granted, of course).',
          featureGate: 'integrations-api',
          featureId: 1,
        },
      ],
      popularity: null,
    },
    {
      author: 'Nisanthan',
      clientId: 'c215db1accc040919e0b0dce058e0ecf4ea062bb82174d70aee8eba62351be24',
      clientSecret: '193583e573d14d61832de96a9efc32ceb64e59a494284f58b50328a656420a55',
      events: [],
      isAlertable: false,
      name: 'ClickUp',
      overview: null,
      owner: {id: 1, slug: 'sentry'},
      redirectUrl: null,
      schema: {},
      scopes: [],
      slug: 'clickup',
      status: 'published',
      uuid: '5d547ecb-7eb8-4ed2-853b-40256177d526',
      verifyInstall: false,
      webhookUrl: 'http://localhost:7000',
      featureData: [
        {
          description:
            'Clickup can **utilize the Sentry API** to pull data or update resources in Sentry (with permissions granted, of course).',
          featureGate: 'integrations-api',
          featureId: 1,
        },
      ],
      popularity: null,
    },
  ];
}

export function PublishedAppsFixture(): SentryApp[] {
  return [
    {
      author: 'Nisanthan',
      clientId: 'c215db1accc040919e0b0dce058e0ecf4ea062bb82174d70aee8eba62351be24',
      clientSecret: '193583e573d14d61832de96a9efc32ceb64e59a494284f58b50328a656420a55',
      events: [],
      isAlertable: false,
      name: 'ClickUp',
      overview: null,
      owner: {id: 1, slug: 'sentry'},
      redirectUrl: null,
      schema: {},
      scopes: [],
      slug: 'clickup',
      status: 'published',
      popularity: 9,
      uuid: '5d547ecb-7eb8-4ed2-853b-40256177d526',
      verifyInstall: false,
      webhookUrl: 'http://localhost:7000',
      featureData: [
        {
          description:
            'Clickup can **utilize the Sentry API** to pull data or update resources in Sentry (with permissions granted, of course).',
          featureGate: 'integrations-api',
          featureId: 1,
        },
      ],
    },
  ];
}

export function SentryAppInstallsFixture() {
  return [
    {
      app: {
        slug: 'my-headband-washer-289499',
        uuid: 'a806ab10-9608-4a4f-8dd9-ca6d6c09f9f5',
      },
      code: 'e5b855d51ad64fa0b6c180ed7e664c5d',
      organization: {slug: 'sentry'},
      status: 'installed',
      uuid: '5379e8e1-0554-468f-90ca-2e0c88f1ac32',
    },
  ];
}

export function PluginListConfigFixture() {
  return [
    {
      author: {name: 'Sentry Team', url: 'https://github.com/getsentry/sentry'},
      canDisable: true,
      contexts: [],
      description: 'Forward Sentry events to Amazon SQS.',
      doc: '',
      featureDescriptions: [
        {
          description: 'Forward Sentry errors and events to Amazon SQS.',
          featureGate: 'data-forwarding',
        },
      ],
      features: ['data-forwarding'],
      hasConfiguration: true,
      id: 'amazon-sqs',
      isHidden: false,
      isTestable: false,
      metadata: {},
      name: 'Amazon SQS',
      projectList: [],
      resourceLinks: [
        {
          title: 'Report Issue',
          url: 'https://github.com/getsentry/sentry/issues',
        },
        {
          title: 'View Source',
          url: 'https://github.com/getsentry/sentry/tree/master/src/sentry_plugins',
        },
      ],
      shortName: 'Amazon SQS',
      slug: 'amazon-sqs',
      status: 'beta',
      type: 'data-forwarding',
      version: '10.1.0.dev0',
    },
    {
      status: 'unknown',
      description: 'Send alerts to PagerDuty.',
      isTestable: true,
      isHidden: true,
      hasConfiguration: true,
      shortName: 'PagerDuty',
      id: 'pagerduty',
      featureDescriptions: [
        {
          description:
            'Configure rule based PagerDuty alerts to automatically be triggered in a specific\n            service - or in multiple services!',
          featureGate: 'alert-rule',
        },
      ],
      features: ['alert-rule'],
      name: 'PagerDuty',
      author: {url: 'https://github.com/getsentry/sentry', name: 'Sentry Team'},
      contexts: [],
      doc: '',
      resourceLinks: [
        {
          url: 'https://github.com/getsentry/sentry/issues',
          title: 'Report Issue',
        },
        {
          url: 'https://github.com/getsentry/sentry/tree/master/src/sentry_plugins',
          title: 'View Source',
        },
      ],
      slug: 'pagerduty',
      projectList: [
        {
          projectId: 2,
          configured: true,
          enabled: true,
          projectSlug: 'javascript',
          projectPlatform: 'javascript',
          projectName: 'JavaScript',
        },
      ],
      version: '10.1.0.dev0',
      canDisable: true,
      type: 'notification',
      metadata: {},
    },
  ];
}

export function WebhookPluginConfigFixture(plugin?: Partial<Plugin>): Plugin {
  return {
    id: 'webhooks',
    name: 'WebHooks',
    slug: 'webhooks',
    shortName: 'WebHooks',
    type: 'notification',
    canDisable: true,
    isTestable: true,
    hasConfiguration: true,
    metadata: {},
    contexts: [],
    status: 'unknown',
    doc: '',
    enabled: true,
    version: '24.1.0.dev0',
    author: {
      name: 'Sentry Team',
      url: 'https://github.com/getsentry/sentry',
    },
    isDeprecated: false,
    isHidden: false,
    description:
      '\nTrigger outgoing HTTP POST requests from Sentry.\n\nNote: To configure webhooks over multiple projects, we recommend setting up an\nInternal Integration.\n',
    features: ['alert-rule'],
    featureDescriptions: [
      {
        description: 'Configure rule based outgoing HTTP POST requests from Sentry.',
        featureGate: 'alert-rule',
        featureId: 1,
      },
    ],
    resourceLinks: [
      {
        title: 'Report Issue',
        url: 'https://github.com/getsentry/sentry/issues',
      },
      {
        title: 'View Source',
        url: 'https://github.com/getsentry/sentry/tree/master/src/sentry/plugins/sentry_webhooks',
      },
      {
        title: 'Internal Integrations',
        url: 'https://docs.sentry.io/workflow/integrations/integration-platform/#internal-integrations',
      },
    ],
    ...plugin,
  };
}
