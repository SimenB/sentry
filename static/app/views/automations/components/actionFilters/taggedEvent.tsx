import AutomationBuilderInputField from 'sentry/components/workflowEngine/form/automationBuilderInputField';
import AutomationBuilderSelectField from 'sentry/components/workflowEngine/form/automationBuilderSelectField';
import {t, tct} from 'sentry/locale';
import type {DataCondition} from 'sentry/types/workflowEngine/dataConditions';
import {
  MATCH_CHOICES,
  type MatchType,
} from 'sentry/views/automations/components/actionFilters/constants';
import {useDataConditionNodeContext} from 'sentry/views/automations/components/dataConditionNodes';

export function TaggedEventDetails({condition}: {condition: DataCondition}) {
  return tct("The event's [key] tag [match] [value]", {
    key: condition.comparison.key,
    match:
      MATCH_CHOICES.find(choice => choice.value === condition.comparison.match)?.label ||
      condition.comparison.match,
    value: condition.comparison.value,
  });
}

export function TaggedEventNode() {
  return tct("The event's [key] [match] [value]", {
    key: <KeyField />,
    match: <MatchField />,
    value: <ValueField />,
  });
}

function KeyField() {
  const {condition, condition_id, onUpdate} = useDataConditionNodeContext();
  return (
    <AutomationBuilderInputField
      name={`${condition_id}.comparison.key`}
      placeholder={t('tag')}
      value={condition.comparison.key}
      onChange={(value: string) => {
        onUpdate({
          key: value,
        });
      }}
    />
  );
}

function MatchField() {
  const {condition, condition_id, onUpdate} = useDataConditionNodeContext();
  return (
    <AutomationBuilderSelectField
      name={`${condition_id}.comparison.match`}
      value={condition.comparison.match}
      options={MATCH_CHOICES}
      onChange={(value: MatchType) => {
        onUpdate({
          match: value,
        });
      }}
    />
  );
}

function ValueField() {
  const {condition, condition_id, onUpdate} = useDataConditionNodeContext();
  return (
    <AutomationBuilderInputField
      name={`${condition_id}.comparison.value`}
      placeholder={t('value')}
      value={condition.comparison.value}
      onChange={(value: string) => {
        onUpdate({
          value,
        });
      }}
    />
  );
}
