// These are the span op we are currently ingesting.

import {SpanFields} from 'sentry/views/insights/types';

// AI Runs - equivalent to OTEL Invoke Agent span
// https://github.com/open-telemetry/semantic-conventions/blob/main/docs/gen-ai/gen-ai-agent-spans.md#invoke-agent-span
const AI_RUN_OPS = [
  'ai.run.generateText',
  'ai.run.generateObject',
  'gen_ai.invoke_agent',
  'ai.pipeline.generate_text',
  'ai.pipeline.generate_object',
  'ai.pipeline.stream_text',
  'ai.pipeline.stream_object',
];

// AI Generations - equivalent to OTEL Inference span
// https://github.com/open-telemetry/semantic-conventions/blob/main/docs/gen-ai/gen-ai-spans.md#inference
export const AI_GENERATION_OPS = [
  'ai.run.doGenerate',
  'gen_ai.chat',
  'gen_ai.generate_content',
  'gen_ai.generate_text',
  'gen_ai.generate_object',
  'gen_ai.stream_text',
  'gen_ai.stream_object',
  'gen_ai.embed', // AI SDK
  'gen_ai.embed_many', // AI SDK
  'gen_ai.embeddings', // Python OpenAI
  'gen_ai.text_completion',
  'gen_ai.responses',
];

// AI Tool Calls - equivalent to OTEL Execute tool span
// https://github.com/open-telemetry/semantic-conventions/blob/main/docs/gen-ai/gen-ai-spans.md#execute-tool-span
export const AI_TOOL_CALL_OPS = ['gen_ai.execute_tool'];

const AI_HANDOFF_OPS = ['gen_ai.handoff'];

const NON_GENERATION_OPS = [...AI_RUN_OPS, ...AI_TOOL_CALL_OPS, ...AI_HANDOFF_OPS];

export const AI_MODEL_ID_ATTRIBUTE = SpanFields.GEN_AI_REQUEST_MODEL;
export const AI_MODEL_NAME_FALLBACK_ATTRIBUTE = SpanFields.GEN_AI_RESPONSE_MODEL;
export const AI_TOOL_NAME_ATTRIBUTE = SpanFields.GEN_AI_TOOL_NAME;
export const AI_COST_ATTRIBUTE = SpanFields.GEN_AI_USAGE_TOTAL_COST;
export const AI_AGENT_NAME_ATTRIBUTE = SpanFields.GEN_AI_AGENT_NAME;
export const AI_TOTAL_TOKENS_ATTRIBUTE = SpanFields.GEN_AI_USAGE_TOTAL_TOKENS;

export const AI_TOKEN_USAGE_ATTRIBUTE_SUM = `sum(${SpanFields.GEN_AI_USAGE_TOTAL_TOKENS})`;
export const AI_INPUT_TOKENS_ATTRIBUTE_SUM = `sum(${SpanFields.GEN_AI_USAGE_INPUT_TOKENS})`;
export const AI_OUTPUT_TOKENS_ATTRIBUTE_SUM = `sum(${SpanFields.GEN_AI_USAGE_OUTPUT_TOKENS})`;
export const AI_OUTPUT_TOKENS_REASONING_ATTRIBUTE_SUM = `sum(${SpanFields.GEN_AI_USAGE_OUTPUT_TOKENS_REASONING})`;
export const AI_INPUT_TOKENS_CACHED_ATTRIBUTE_SUM = `sum(${SpanFields.GEN_AI_USAGE_INPUT_TOKENS_CACHED})`;
export const AI_COST_ATTRIBUTE_SUM = `sum(${SpanFields.GEN_AI_USAGE_TOTAL_COST})`;

export const legacyAttributeKeys = new Map<string, string[]>([
  ['gen_ai.request.model', ['ai.model.id']],
  ['gen_ai.usage.input_tokens', ['ai.prompt_tokens.used']],
  ['gen_ai.usage.output_tokens', ['ai.completion_tokens.used']],
  ['gen_ai.usage.total_tokens', ['ai.total_tokens.used']],
  ['gen_ai.usage.total_cost', ['ai.total_cost.used']],
  ['gen_ai.tool.input', ['ai.toolCall.args']],
  ['gen_ai.tool.output', ['ai.toolCall.result']],
  ['gen_ai.request.messages', ['ai.prompt.messages']],
  ['gen_ai.prompt', ['ai.prompt']],
  ['gen_ai.response.tool_calls', ['ai.response.toolCalls']],
  ['gen_ai.response.text', ['ai.response.text']],
  ['gen_ai.response.object', ['ai.response.object']],
  ['gen_ai.tool.name', ['ai.toolCall.name']],
]);

export function extendWithLegacyAttributeKeys(attributeKeys: string[]) {
  return attributeKeys.flatMap(key => {
    const legacyKeys = legacyAttributeKeys.get(key) ?? [];
    return [key, ...legacyKeys];
  });
}

export function getIsAiSpan({op = 'default'}: {op?: string}) {
  return op.startsWith('gen_ai.');
}

export function getIsAiRunSpan({op = 'default'}: {op?: string}) {
  return AI_RUN_OPS.includes(op);
}

// All of the gen_ai.* spans that are not agent invocations, handoffs, or tool calls are considered generation spans
export function getIsAiGenerationSpan({op = 'default'}: {op?: string}) {
  return op.startsWith('gen_ai.') && !NON_GENERATION_OPS.includes(op);
}

export function getIsAiToolCallSpan({op = 'default'}: {op?: string}) {
  return AI_TOOL_CALL_OPS.includes(op);
}

export function getIsAiHandoffSpan({op = 'default'}: {op?: string}) {
  return AI_HANDOFF_OPS.includes(op);
}

function joinValues(values: string[]) {
  return values.map(value => `"${value}"`).join(',');
}

export const getAgentRunsFilter = ({negated = false}: {negated?: boolean} = {}) => {
  return `${negated ? '!' : ''}span.op:[${joinValues(AI_RUN_OPS)}]`;
};

// All of the gen_ai.* spans that are not agent invocations, handoffs, or tool calls are considered generation spans
export const getAIGenerationsFilter = () => {
  return `span.op:gen_ai.* !span.op:[${joinValues(NON_GENERATION_OPS)}]`;
};

export const getAIToolCallsFilter = () => {
  return `span.op:[${joinValues(AI_TOOL_CALL_OPS)}]`;
};

export const getAITracesFilter = () => {
  return `span.op:gen_ai.*`;
};
