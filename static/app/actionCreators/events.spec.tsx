import {OrganizationFixture} from 'sentry-fixture/organization';
import {ProjectFixture} from 'sentry-fixture/project';

import {doEventsRequest} from 'sentry/actionCreators/events';

describe('Events ActionCreator', function () {
  const api = new MockApiClient();
  const organization = OrganizationFixture();
  const project = ProjectFixture();
  const opts = {
    organization,
    project: [parseInt(project.id, 10)],
    environment: [],
  };

  let mock: jest.Mock;

  beforeEach(function () {
    MockApiClient.clearMockResponses();
    mock = MockApiClient.addMockResponse({
      url: '/organizations/org-slug/events-stats/',
      body: {
        data: [
          [123, []],
          [123, []],
          [123, []],
          [123, []],
          [123, []],
          [123, []],
        ],
      },
    });
  });

  it('requests events stats with relative period', async function () {
    await doEventsRequest<false>(api, {
      ...opts,
      includeAllArgs: false,
      includePrevious: false,
      period: '7d',
      partial: true,
    });

    expect(mock).toHaveBeenLastCalledWith(
      '/organizations/org-slug/events-stats/',
      expect.objectContaining({
        query: expect.objectContaining({
          project: [parseInt(project.id, 10)],
          environment: [],
          statsPeriod: '7d',
        }),
      })
    );
  });

  it('requests events stats with relative period including previous period', async function () {
    await doEventsRequest<false>(api, {
      ...opts,
      includeAllArgs: false,
      includePrevious: true,
      period: '7d',
      partial: true,
    });

    expect(mock).toHaveBeenLastCalledWith(
      '/organizations/org-slug/events-stats/',
      expect.objectContaining({
        query: expect.objectContaining({
          project: [parseInt(project.id, 10)],
          environment: [],
          statsPeriod: '14d',
        }),
      })
    );
  });

  it('requests events stats with absolute period', async function () {
    const start = new Date('2017-10-12T12:00:00.000Z');
    const end = new Date('2017-10-17T00:00:00.000Z');
    await doEventsRequest<false>(api, {
      ...opts,
      includeAllArgs: false,
      includePrevious: false,
      start,
      end,
      partial: true,
    });

    expect(mock).toHaveBeenCalledTimes(1);
    expect(mock).toHaveBeenLastCalledWith(
      '/organizations/org-slug/events-stats/',
      expect.objectContaining({
        query: expect.objectContaining({
          project: [parseInt(project.id, 10)],
          environment: [],
          start: '2017-10-12T12:00:00',
          end: '2017-10-17T00:00:00',
        }),
      })
    );
  });

  it('requests events stats with absolute period including previous period', async function () {
    const start = new Date('2017-10-12T12:00:00.000Z');
    const end = new Date('2017-10-17T00:00:00.000Z');
    await doEventsRequest<false>(api, {
      ...opts,
      includeAllArgs: false,
      includePrevious: true,
      start,
      end,
      partial: true,
    });

    expect(mock).toHaveBeenLastCalledWith(
      '/organizations/org-slug/events-stats/',
      expect.objectContaining({
        query: expect.objectContaining({
          project: [parseInt(project.id, 10)],
          environment: [],
          start: '2017-10-08T00:00:00',
          end: '2017-10-17T00:00:00',
        }),
      })
    );
  });

  it('spreads query extras', async function () {
    await doEventsRequest<false>(api, {
      ...opts,
      includeAllArgs: false,
      queryExtras: {useOnDemandMetrics: 'true'},
      partial: true,
    });

    expect(mock).toHaveBeenLastCalledWith(
      '/organizations/org-slug/events-stats/',
      expect.objectContaining({
        query: expect.objectContaining({
          project: [parseInt(project.id, 10)],
          environment: [],
          useOnDemandMetrics: 'true',
        }),
      })
    );
  });
});
