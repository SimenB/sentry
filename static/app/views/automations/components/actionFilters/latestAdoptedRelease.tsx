import {AutomationBuilderSelect} from 'sentry/components/workflowEngine/form/automationBuilderSelect';
import {t, tct} from 'sentry/locale';
import type {SelectValue} from 'sentry/types/core';
import type {Environment} from 'sentry/types/project';
import type {DataCondition} from 'sentry/types/workflowEngine/dataConditions';
import {useApiQuery} from 'sentry/utils/queryClient';
import useOrganization from 'sentry/utils/useOrganization';
import {
  AGE_COMPARISON_CHOICES,
  type AgeComparison,
  MODEL_AGE_CHOICES,
  type ModelAge,
} from 'sentry/views/automations/components/actionFilters/constants';
import {useAutomationBuilderErrorContext} from 'sentry/views/automations/components/automationBuilderErrorContext';
import type {ValidateDataConditionProps} from 'sentry/views/automations/components/automationFormData';
import {useDataConditionNodeContext} from 'sentry/views/automations/components/dataConditionNodes';

export function LatestAdoptedReleaseDetails({condition}: {condition: DataCondition}) {
  return tct(
    "The [releaseAgeType] adopted release associated with the event's issue is [ageComparison] the latest adopted release in [environment]",
    {
      releaseAgeType:
        MODEL_AGE_CHOICES.find(
          choice => choice.value === condition.comparison.releaseAgeType
        )?.label || condition.comparison.releaseAgeType,
      ageComparison:
        AGE_COMPARISON_CHOICES.find(
          choice => choice.value === condition.comparison.ageComparison
        )?.label || condition.comparison.ageComparison,
      environment: condition.comparison.environment,
    }
  );
}

export function LatestAdoptedReleaseNode() {
  return tct(
    "The [releaseAgeType] adopted release associated with the event's issue is [ageComparison] the latest adopted release in [environment]",
    {
      releaseAgeType: <ReleaseAgeTypeField />,
      ageComparison: <AgeComparisonField />,
      environment: <EnvironmentField />,
    }
  );
}

function ReleaseAgeTypeField() {
  const {condition, condition_id, onUpdate} = useDataConditionNodeContext();
  return (
    <AutomationBuilderSelect
      name={`${condition_id}.comparison.releaseAgeType`}
      aria-label={t('Release age type')}
      value={condition.comparison.releaseAgeType}
      options={MODEL_AGE_CHOICES}
      onChange={(option: SelectValue<ModelAge>) => {
        onUpdate({comparison: {...condition.comparison, releaseAgeType: option.value}});
      }}
    />
  );
}

function AgeComparisonField() {
  const {condition, condition_id, onUpdate} = useDataConditionNodeContext();
  return (
    <AutomationBuilderSelect
      name={`${condition_id}.comparison.ageComparison`}
      aria-label={t('Age comparison')}
      value={condition.comparison.ageComparison}
      options={AGE_COMPARISON_CHOICES}
      onChange={(option: SelectValue<AgeComparison>) => {
        onUpdate({comparison: {...condition.comparison, ageComparison: option.value}});
      }}
    />
  );
}

function EnvironmentField() {
  const {condition, condition_id, onUpdate} = useDataConditionNodeContext();
  const {removeError} = useAutomationBuilderErrorContext();

  const {environments} = useOrganizationEnvironments();
  const environmentOptions = environments.map(({id, name}) => ({
    value: id,
    label: name,
  }));

  return (
    <AutomationBuilderSelect
      name={`${condition_id}.comparison.environment`}
      aria-label={t('Environment')}
      value={condition.comparison.environment}
      options={environmentOptions}
      placeholder={t('environment')}
      onChange={(option: SelectValue<string>) => {
        onUpdate({comparison: {...condition.comparison, environment: option.value}});
        // We only remove the error when `environment` is changed since
        // other fields have default values and should not trigger an error
        removeError(condition.id);
      }}
    />
  );
}

function useOrganizationEnvironments() {
  const organization = useOrganization();
  const {data: environments = [], isLoading} = useApiQuery<Environment[]>(
    [
      `/organizations/${organization.slug}/environments/`,
      {query: {visibility: 'visible'}},
    ],
    {
      staleTime: 30_000,
    }
  );
  return {environments, isLoading};
}

export function validateLatestAdoptedReleaseCondition({
  condition,
}: ValidateDataConditionProps): string | undefined {
  if (
    !condition.comparison.releaseAgeType ||
    !condition.comparison.ageComparison ||
    !condition.comparison.environment
  ) {
    return t('Ensure all fields are filled in.');
  }
  return undefined;
}
