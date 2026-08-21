/** Model-aware reasoning effort policy shared by Desktop pickers. */

export const GENERIC_REASONING_EFFORTS = ['minimal', 'low', 'medium', 'high', 'xhigh', 'max', 'ultra'] as const
export const DEEPSEEK_V4_REASONING_EFFORTS = ['low', 'high', 'max'] as const

export function isDeepSeekV4Model(model: string): boolean {
  const normalized = String(model ?? '').trim().toLowerCase()

  if (!normalized) {
    return false
  }

  const modelId = normalized.split('/').pop()?.split(':')[0] ?? ''

  return modelId.startsWith('deepseek-v4-')
}

/** Includes `none`, which is the thinking-off toggle rather than an effort. */
export function reasoningEffortValuesForModel(model: string): readonly string[] {
  return isDeepSeekV4Model(model)
    ? ['none', ...DEEPSEEK_V4_REASONING_EFFORTS]
    : ['none', ...GENERIC_REASONING_EFFORTS]
}

export function defaultReasoningEffortForModel(model: string): string {
  return isDeepSeekV4Model(model) ? 'high' : 'medium'
}

export function normalizeReasoningEffort(value: unknown, model = ''): string {
  if (value === false) {
    return 'none'
  }

  const effort = String(value ?? '').trim().toLowerCase()

  if (!effort) {
    return defaultReasoningEffortForModel(model)
  }

  if (effort === 'false' || effort === 'disabled' || effort === 'off' || effort === 'none') {
    return 'none'
  }

  return reasoningEffortValuesForModel(model).includes(effort)
    ? effort
    : defaultReasoningEffortForModel(model)
}
