import {Fragment} from 'react';
import styled from '@emotion/styled';

import {ProjectAvatar} from 'sentry/components/core/avatar/projectAvatar';
import {ExternalLink} from 'sentry/components/core/link';
import useStacktraceLink from 'sentry/components/events/interfaces/frame/useStacktraceLink';
import {t, tct} from 'sentry/locale';
import {space} from 'sentry/styles/space';
import type {Project} from 'sentry/types/project';
import {getIntegrationIcon, getIntegrationSourceUrl} from 'sentry/utils/integrationUtil';
import useOrganization from 'sentry/utils/useOrganization';
import useProjects from 'sentry/utils/useProjects';
import {MODULE_DOC_LINK} from 'sentry/views/insights/database/settings';

interface Props {
  frame: Parameters<typeof useStacktraceLink>[0]['frame'];
  event?: Parameters<typeof useStacktraceLink>[0]['event'];
  projectId?: string;
}

export function StackTraceMiniFrame({frame, event, projectId}: Props) {
  const {projects} = useProjects();
  const project = projects.find(p => p.id === projectId);

  return (
    <FrameContainer>
      {project && (
        <ProjectAvatarContainer>
          <ProjectAvatar project={project} size={16} />
        </ProjectAvatarContainer>
      )}
      {frame.filename && <Emphasize>{frame?.filename}</Emphasize>}
      {frame.function && (
        <Fragment>
          <Deemphasize> {t('in')} </Deemphasize>
          <Emphasize>{frame?.function}</Emphasize>
        </Fragment>
      )}
      {frame.lineNo && (
        <Fragment>
          <Deemphasize> {t('at line')} </Deemphasize>
          <Emphasize>{frame?.lineNo}</Emphasize>
        </Fragment>
      )}

      {event && project && (
        <PushRight>
          <SourceCodeIntegrationLink event={event} project={project} frame={frame} />
        </PushRight>
      )}
    </FrameContainer>
  );
}

type MissingFrameProps = {
  system?: string;
};

export function MissingFrame({system}: MissingFrameProps) {
  const documentation = <ExternalLink href={`${MODULE_DOC_LINK}#query-sources`} />;

  const errorMessage =
    system === 'mongodb'
      ? tct(
          'Query sources are not currently supported for MongoDB queries. Learn more in our [documentation:documentation].',
          {documentation}
        )
      : tct(
          'Could not find query source in the selected date range. Learn more in our [documentation:documentation].',
          {documentation}
        );

  return (
    <FrameContainer>
      <Deemphasize>{errorMessage}</Deemphasize>
    </FrameContainer>
  );
}

export const FrameContainer = styled('div')`
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: ${space(0.5)};
  padding: ${space(1.5)} ${space(2)};

  font-family: ${p => p.theme.text.family};
  font-size: ${p => p.theme.fontSize.md};

  border-top: 1px solid ${p => p.theme.border};

  background: ${p => p.theme.surface200};
`;

const ProjectAvatarContainer = styled('div')`
  margin-right: ${space(1)};
`;

const Emphasize = styled('span')`
  color: ${p => p.theme.gray500};
`;

const Deemphasize = styled('span')`
  color: ${p => p.theme.subText};
`;

const PushRight = styled('span')`
  margin-left: auto;
`;

interface SourceCodeIntegrationLinkProps {
  event: Parameters<typeof useStacktraceLink>[0]['event'];
  frame: Parameters<typeof useStacktraceLink>[0]['frame'];
  project: Project;
}
function SourceCodeIntegrationLink({
  event,
  project,
  frame,
}: SourceCodeIntegrationLinkProps) {
  const organization = useOrganization();

  const {data: match, isPending} = useStacktraceLink({
    event,
    frame,
    orgSlug: organization.slug,
    projectSlug: project.slug,
  });

  if (match?.config && match.sourceUrl && frame.lineNo && !isPending) {
    return (
      <DeemphasizedExternalLink
        href={getIntegrationSourceUrl(
          match.config.provider.key,
          match.sourceUrl,
          frame.lineNo
        )}
        openInNewTab
      >
        <StyledIconWrapper>
          {getIntegrationIcon(match.config.provider.key, 'sm')}
        </StyledIconWrapper>
        {t('Open this line in %s', match.config.provider.name)}
      </DeemphasizedExternalLink>
    );
  }

  return null;
}

const DeemphasizedExternalLink = styled(ExternalLink)`
  display: flex;
  align-items: center;
  gap: ${space(0.75)};
  color: ${p => p.theme.subText};
`;

const StyledIconWrapper = styled('span')`
  color: inherit;
  line-height: 0;
`;
