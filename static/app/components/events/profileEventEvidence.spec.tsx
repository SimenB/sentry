import {EventFixture} from 'sentry-fixture/event';
import {GroupFixture} from 'sentry-fixture/group';

import {render, screen} from 'sentry-test/reactTestingLibrary';

import {ProfileEventEvidence} from 'sentry/components/events/profileEventEvidence';
import {IssueType} from 'sentry/types/group';

describe('ProfileEventEvidence', function () {
  const defaultProps = {
    event: EventFixture({
      id: 'event-id',
      occurrence: {
        evidenceDisplay: [{name: 'Evidence name', value: 'Evidence value'}],
        evidenceData: {
          profileId: 'profile-id',
          frameName: 'some_func',
          framePackage: 'something.dll',
          transactionId: 'transaction-id',
          transactionName: 'SomeTransaction',
          templateName: 'profile',
        },
      },
      contexts: {
        trace: {
          trace_id: 'trace-id',
        },
      },
    }),
    group: GroupFixture({
      issueType: IssueType.PROFILE_FILE_IO_MAIN_THREAD,
    }),
    projectSlug: 'project-slug',
  };

  it('displays profile ID and data in evidence display', function () {
    render(<ProfileEventEvidence {...defaultProps} />);

    expect(screen.getByRole('cell', {name: 'Transaction Name'})).toBeInTheDocument();
    expect(screen.getByRole('cell', {name: /SomeTransaction/})).toBeInTheDocument();

    expect(screen.getByRole('cell', {name: 'Profile ID'})).toBeInTheDocument();
    expect(screen.getByRole('cell', {name: /profile-id/})).toBeInTheDocument();

    expect(screen.getByRole('cell', {name: 'Evidence name'})).toBeInTheDocument();
    expect(screen.getByRole('cell', {name: 'Evidence value'})).toBeInTheDocument();
  });

  it('correctly links to the profile frame', function () {
    render(<ProfileEventEvidence {...defaultProps} />);

    expect(screen.getByRole('button', {name: 'View Profile'})).toHaveAttribute(
      'href',
      '/organizations/org-slug/profiling/profile/project-slug/profile-id/flamegraph/?frameName=some_func&framePackage=something.dll&referrer=issue'
    );
  });

  it('correctly links to the transaction', function () {
    render(<ProfileEventEvidence {...defaultProps} />);

    expect(screen.getByRole('button', {name: 'View Transaction'})).toHaveAttribute(
      'href',
      '/organizations/org-slug/traces/trace/trace-id/?referrer=issue&statsPeriod=14d'
    );
  });
});
