import {Fragment, useState} from 'react';
import styled from '@emotion/styled';
import keyBy from 'lodash/keyBy';

import {Button} from 'sentry/components/core/button';
import {Select} from 'sentry/components/core/select';
import EmptyStateWarning from 'sentry/components/emptyStateWarning';
import IdBadge from 'sentry/components/idBadge';
import LoadingError from 'sentry/components/loadingError';
import LoadingIndicator from 'sentry/components/loadingIndicator';
import Panel from 'sentry/components/panels/panel';
import PanelBody from 'sentry/components/panels/panelBody';
import PanelHeader from 'sentry/components/panels/panelHeader';
import {IconAdd, IconDelete} from 'sentry/icons';
import {t} from 'sentry/locale';
import ConfigStore from 'sentry/stores/configStore';
import {space} from 'sentry/styles/space';
import type {Organization} from 'sentry/types/organization';
import type {Project} from 'sentry/types/project';
import {useApiQuery} from 'sentry/utils/queryClient';
import useRouter from 'sentry/utils/useRouter';

import type {NotificationOptionsObject, NotificationSettingsType} from './constants';
import {NOTIFICATION_SETTING_FIELDS} from './fields2';
import {OrganizationSelectHeader} from './organizationSelectHeader';

type Value = 'always' | 'never' | 'subscribe_only' | 'committed_only';

interface NotificationSettingsByEntityProps {
  entityType: 'project' | 'organization';
  handleAddNotificationOption: (
    notificationOption: Omit<NotificationOptionsObject, 'id'>
  ) => void;
  handleEditNotificationOption: (notificationOption: NotificationOptionsObject) => void;
  handleRemoveNotificationOption: (id: string) => void;
  notificationOptions: NotificationOptionsObject[];
  notificationType: string;
  organizations: Organization[];
}

function NotificationSettingsByEntity({
  entityType,
  handleAddNotificationOption,
  handleEditNotificationOption,
  handleRemoveNotificationOption,
  notificationOptions,
  notificationType,
  organizations,
}: NotificationSettingsByEntityProps) {
  const router = useRouter();
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null);
  const [selectedValue, setSelectedValue] = useState<Value | null>(null);

  const customerDomain = ConfigStore.get('customerDomain');
  const orgFromSubdomain = organizations.find(
    ({slug}) => slug === customerDomain?.subdomain
  )?.id;

  const orgId =
    router.location?.query?.organizationId ??
    orgFromSubdomain ??
    (organizations.length === 1 ? organizations[0]?.id : undefined);
  let organization = organizations.find(({id}) => id === orgId);

  if (!organization && organizations.length === 1) {
    organization = organizations[0];
  }
  const orgSlug = organization?.slug;

  // loads all the projects for an org
  const {
    data: projects,
    isPending,
    isSuccess,
    isError,
    refetch,
  } = useApiQuery<Project[]>(
    [
      `/organizations/${orgSlug}/projects/`,
      {
        host: organization?.links?.regionUrl,
        query: {
          all_projects: '1',
          collapse: ['latestDeploys', 'unusedFeatures'],
        },
      },
    ],
    {staleTime: Infinity, enabled: Boolean(organization)}
  );

  // always loading all projects even though we only need it sometimes
  const entities = entityType === 'project' ? projects || [] : organizations;
  // create maps by the project id for constant time lookups
  const entityById = keyBy<Organization | Project>(entities, 'id');

  const handleOrgChange = (organizationId: string) => {
    router.replace({
      ...router.location,
      query: {organizationId},
    });
  };

  const handleAdd = () => {
    // should never happen
    if (!selectedEntityId || !selectedValue) {
      return;
    }
    const data = {
      type: notificationType,
      scopeType: entityType,
      scopeIdentifier: selectedEntityId,
      value: selectedValue,
    };
    setSelectedEntityId(null);
    setSelectedValue(null);
    handleAddNotificationOption(data);
  };

  const valueOptions =
    NOTIFICATION_SETTING_FIELDS[notificationType as NotificationSettingsType].choices;

  const renderOverrides = () => {
    const matchedOptions = notificationOptions.filter(
      option => option.type === notificationType && option.scopeType === entityType
    );
    return matchedOptions.map(option => {
      const entity = entityById[`${option.scopeIdentifier}`];
      if (!entity) {
        return null;
      }

      const idBadgeProps =
        entityType === 'project'
          ? {project: entity as Project}
          : {organization: entity as Organization};

      return (
        <Item key={entity.id}>
          <div style={{marginLeft: space(2)}}>
            <IdBadge
              {...idBadgeProps}
              avatarSize={20}
              displayName={entity.slug}
              avatarProps={{consistentWidth: true}}
              disableLink
            />
          </div>
          <Select
            placeholder={t('Value\u2026')}
            value={option.value}
            name={`${entity.id}-value`}
            choices={valueOptions}
            onChange={({value}: {value: string}) => {
              handleEditNotificationOption({
                ...option,
                value: value as Value,
              });
            }}
          />
          <RemoveButtonWrapper>
            <Button
              aria-label={t('Delete')}
              size="sm"
              priority="default"
              icon={<IconDelete />}
              onClick={() => handleRemoveNotificationOption(option.id)}
            />
          </RemoveButtonWrapper>
        </Item>
      );
    });
  };

  const entityOptions = entities
    .filter(({id}: any) => {
      const match = notificationOptions.find(
        option =>
          option.scopeType === entityType &&
          option.scopeIdentifier.toString() === id.toString() &&
          option.type === notificationType
      );
      return !match;
    })
    .map((obj: any) => {
      const entity = entityById[obj.id];
      const idBadgeProps =
        entityType === 'project'
          ? {project: entity as Project}
          : {organization: entity as Organization};

      return {
        label: entityType === 'project' ? obj.slug : obj.name,
        value: obj.id,
        leadingItems: (
          <IdBadge
            {...idBadgeProps}
            avatarSize={20}
            avatarProps={{consistentWidth: true}}
            disableLink
            hideName
          />
        ),
      };
    })
    .sort((a: any, b: any) => a.label.localeCompare(b.label));

  // Group options when displaying projects
  const groupedEntityOptions =
    entityType === 'project'
      ? [
          {
            label: t('My Projects'),
            options: entityOptions.filter(
              (project: any) => (entityById[project.value] as Project).isMember
            ),
          },
          {
            label: t('All Projects'),
            options: entityOptions.filter(
              (project: any) => !(entityById[project.value] as Project).isMember
            ),
          },
        ]
      : entityOptions;

  return (
    <MinHeight>
      <Panel>
        <StyledPanelHeader>
          {entityType === 'project' ? (
            <OrganizationSelectHeader
              organizations={organizations}
              organizationId={orgId}
              handleOrgChange={handleOrgChange}
            />
          ) : (
            t('Settings for Organizations')
          )}
        </StyledPanelHeader>
        {!organization && entityType === 'project' ? (
          <PanelBody>
            <EmptyStateWarning withIcon={false}>
              {t('Select an organization to continue')}
            </EmptyStateWarning>
          </PanelBody>
        ) : (
          <Fragment>
            <ControlItem>
              {/* TODO: enable search for sentry projects */}
              <Select
                placeholder={
                  entityType === 'project'
                    ? t('Project\u2026')
                    : t('Sentry Organization\u2026')
                }
                name={entityType}
                options={groupedEntityOptions}
                onChange={({value}: {value: string}) => {
                  setSelectedEntityId(value);
                }}
                value={selectedEntityId}
              />
              <Select
                placeholder={t('Value\u2026')}
                value={selectedValue}
                name="value"
                choices={valueOptions}
                onChange={({value}: {value: string}) => {
                  setSelectedValue(value as Value);
                }}
              />
              <Button
                disabled={!selectedEntityId || !selectedValue}
                priority="primary"
                onClick={handleAdd}
                icon={<IconAdd />}
                aria-label={t('Add override')}
              />
            </ControlItem>
            {isPending && entityType === 'project' && (
              <PanelBody>
                <LoadingIndicator />
              </PanelBody>
            )}
            {isError && entityType === 'project' && (
              <PanelBody>
                <LoadingError onRetry={refetch} />
              </PanelBody>
            )}
            {(isSuccess || entityType === 'organization') && (
              <StyledPanelBody>{renderOverrides()}</StyledPanelBody>
            )}
          </Fragment>
        )}
      </Panel>
    </MinHeight>
  );
}

export default NotificationSettingsByEntity;

const MinHeight = styled('div')`
  min-height: 400px;
`;

const StyledPanelHeader = styled(PanelHeader)`
  flex-wrap: wrap;
  gap: ${space(1)};
  & > form:last-child {
    flex-grow: 1;
  }
`;

const StyledPanelBody = styled(PanelBody)`
  & > div:not(:last-child) {
    border-bottom: 1px solid ${p => p.theme.innerBorder};
  }
`;

const Item = styled('div')`
  display: grid;
  grid-column-gap: ${space(1)};
  grid-template-columns: 2.5fr 1fr min-content;
  align-items: center;
  padding: ${space(1.5)} ${space(2)};
`;

const ControlItem = styled(Item)`
  border-bottom: 1px solid ${p => p.theme.innerBorder};
`;

const RemoveButtonWrapper = styled('div')`
  margin: 0 ${space(0.5)};
`;
