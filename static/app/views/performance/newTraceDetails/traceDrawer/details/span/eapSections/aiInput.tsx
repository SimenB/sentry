import {Fragment} from 'react';
import * as Sentry from '@sentry/react';

import {StructuredData} from 'sentry/components/structuredEventData';
import {t} from 'sentry/locale';
import type {EventTransaction} from 'sentry/types/event';
import {defined} from 'sentry/utils';
import useOrganization from 'sentry/utils/useOrganization';
import type {TraceItemResponseAttribute} from 'sentry/views/explore/hooks/useTraceItemDetails';
import {hasAgentInsightsFeature} from 'sentry/views/insights/agentMonitoring/utils/features';
import {
  getIsAiNode,
  getTraceNodeAttribute,
} from 'sentry/views/insights/agentMonitoring/utils/highlightedSpanAttributes';
import {SectionKey} from 'sentry/views/issueDetails/streamline/context';
import {FoldSection} from 'sentry/views/issueDetails/streamline/foldSection';
import {TraceDrawerComponents} from 'sentry/views/performance/newTraceDetails/traceDrawer/details/styles';
import type {TraceTree} from 'sentry/views/performance/newTraceDetails/traceModels/traceTree';
import type {TraceTreeNode} from 'sentry/views/performance/newTraceDetails/traceModels/traceTreeNode';

function renderUserMessage(content: any) {
  return content
    .filter((part: any) => part.type === 'text')
    .map((part: any) => part.text)
    .join('\n');
}

function renderAssistantMessage(content: any) {
  return content
    .filter((part: any) => part.type === 'text')
    .map((part: any) => part.text)
    .join('\n');
}

function renderToolMessage(content: any) {
  return <StructuredData value={content} maxDefaultDepth={2} withAnnotatedText />;
}

function parseAIMessages(messages: string) {
  try {
    const array: any[] = JSON.parse(messages);

    return array
      .map((message: any) => {
        switch (message.role) {
          case 'system':
            return {
              role: 'system' as const,
              content: message.content.toString(),
            };
          case 'user':
            return {
              role: 'user' as const,
              content: renderUserMessage(message.content),
            };
          case 'assistant':
            return {
              role: 'assistant' as const,
              content: renderAssistantMessage(message.content),
            };
          case 'tool':
            return {
              role: 'tool' as const,
              content: renderToolMessage(message.content),
            };
          default:
            Sentry.captureMessage('Unknown AI message role', {
              extra: {
                role: message.role,
              },
            });
            return null;
        }
      })
      .filter(message => message !== null);
  } catch (error) {
    Sentry.captureMessage('Error parsing ai.prompt.messages', {
      extra: {
        error,
      },
    });
    return messages;
  }
}

function transformInputMessages(inputMessages: string) {
  try {
    const json = JSON.parse(inputMessages);
    const result = [];
    const {system, prompt} = json;
    if (system) {
      result.push({
        role: 'system',
        content: system,
      });
    }
    if (prompt) {
      result.push({
        role: 'user',
        content: [{type: 'text', text: prompt}],
      });
    }
    return JSON.stringify(result);
  } catch (error) {
    Sentry.captureMessage('Error parsing ai.input_messages', {
      extra: {
        error,
      },
    });
    return undefined;
  }
}

const roleHeadings = {
  system: t('System'),
  user: t('User'),
  assistant: t('Assistant'),
  tool: t('Tool'),
};

export function AIInputSection({
  node,
  attributes,
  event,
}: {
  node: TraceTreeNode<TraceTree.EAPSpan | TraceTree.Span | TraceTree.Transaction>;
  attributes?: TraceItemResponseAttribute[];
  event?: EventTransaction;
}) {
  const organization = useOrganization();
  if (!hasAgentInsightsFeature(organization) && getIsAiNode(node)) {
    return null;
  }

  let promptMessages = getTraceNodeAttribute(
    'ai.prompt.messages',
    node,
    event,
    attributes
  );
  if (!promptMessages) {
    const inputMessages = getTraceNodeAttribute(
      'ai.input_messages',
      node,
      event,
      attributes
    );
    promptMessages = transformInputMessages(inputMessages);
  }

  const aiInput = defined(promptMessages) && parseAIMessages(promptMessages as string);

  if (!aiInput) {
    return null;
  }

  return (
    <FoldSection
      sectionKey={SectionKey.AI_INPUT}
      title={t('Input')}
      disableCollapsePersistence
    >
      {/* If parsing fails, we'll just show the raw string */}
      {typeof aiInput === 'string' ? (
        <TraceDrawerComponents.MultilineText>
          {aiInput}
        </TraceDrawerComponents.MultilineText>
      ) : (
        <Fragment>
          {aiInput.map((message, index) => (
            <Fragment key={index}>
              <TraceDrawerComponents.MultilineTextLabel>
                {roleHeadings[message.role]}
              </TraceDrawerComponents.MultilineTextLabel>
              <TraceDrawerComponents.MultilineText>
                {message.content}
              </TraceDrawerComponents.MultilineText>
            </Fragment>
          ))}
        </Fragment>
      )}
    </FoldSection>
  );
}
