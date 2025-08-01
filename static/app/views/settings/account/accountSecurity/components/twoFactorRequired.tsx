import styled from '@emotion/styled';

import {Alert} from 'sentry/components/core/alert';
import {ExternalLink} from 'sentry/components/core/link';
import {tct} from 'sentry/locale';
import {space} from 'sentry/styles/space';
import getPendingInvite from 'sentry/utils/getPendingInvite';

function TwoFactorRequired() {
  return getPendingInvite() ? (
    <StyledAlert data-test-id="require-2fa" type="error">
      {tct(
        'You have been invited to an organization that requires [link:two-factor authentication]. Setup two-factor authentication below to join your organization.',
        {
          link: <ExternalLink href="https://docs.sentry.io/accounts/require-2fa/" />,
        }
      )}
    </StyledAlert>
  ) : null;
}

const StyledAlert = styled(Alert)`
  margin: ${space(3)} 0;
`;

export default TwoFactorRequired;
