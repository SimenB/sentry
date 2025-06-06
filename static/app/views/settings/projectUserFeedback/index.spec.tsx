import {ProjectFixture} from 'sentry-fixture/project';

import {initializeOrg} from 'sentry-test/initializeOrg';
import {render, screen, userEvent} from 'sentry-test/reactTestingLibrary';

import ProjectUserFeedback from 'sentry/views/settings/projectUserFeedback';

describe('ProjectUserFeedback', function () {
  const {routerProps, organization, project} = initializeOrg();
  const url = `/projects/${organization.slug}/${project.slug}/`;

  beforeEach(function () {
    MockApiClient.clearMockResponses();
    MockApiClient.addMockResponse({
      url,
      method: 'GET',
      body: ProjectFixture(),
    });
    MockApiClient.addMockResponse({
      url: `${url}keys/`,
      method: 'GET',
      body: [],
    });
  });

  it('can toggle sentry branding option', async function () {
    render(
      <ProjectUserFeedback
        {...routerProps}
        organization={organization}
        project={project}
      />
    );

    const mock = MockApiClient.addMockResponse({
      url,
      method: 'PUT',
    });

    await userEvent.click(
      screen.getByRole('checkbox', {name: 'Show Sentry Branding in Crash Report Modal'})
    );

    expect(mock).toHaveBeenCalledWith(
      url,
      expect.objectContaining({
        method: 'PUT',
        data: {
          options: {'feedback:branding': true},
        },
      })
    );
  });
});

describe('ProjectUserFeedbackProcessing', function () {
  const {routerProps, organization, project} = initializeOrg();
  const url = `/projects/${organization.slug}/${project.slug}/`;

  beforeEach(function () {
    MockApiClient.clearMockResponses();
    MockApiClient.addMockResponse({
      url,
      method: 'GET',
      body: ProjectFixture(),
    });
    MockApiClient.addMockResponse({
      url: `${url}keys/`,
      method: 'GET',
      body: [],
    });
    organization.features = [];
  });

  it('cannot toggle spam detection', function () {
    render(
      <ProjectUserFeedback
        {...routerProps}
        organization={organization}
        project={project}
      />
    );

    expect(
      screen.queryByRole('checkbox', {name: 'Enable Spam Detection'})
    ).not.toBeInTheDocument();
  });

  it('can toggle spam detection', async function () {
    organization.features.push('user-feedback-spam-ingest');

    render(
      <ProjectUserFeedback
        {...routerProps}
        organization={organization}
        project={project}
      />
    );

    const mock = MockApiClient.addMockResponse({
      url,
      method: 'PUT',
    });

    await userEvent.click(screen.getByRole('checkbox', {name: 'Enable Spam Detection'}));

    expect(mock).toHaveBeenCalledWith(
      url,
      expect.objectContaining({
        method: 'PUT',
        data: {
          options: {'sentry:feedback_ai_spam_detection': true},
        },
      })
    );
  });
});
