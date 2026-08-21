import { describe, expect, it } from 'vitest'

import {
  defaultReasoningEffortForModel,
  isDeepSeekV4Model,
  normalizeReasoningEffort,
  reasoningEffortValuesForModel
} from './reasoning-effort'

describe('model-aware reasoning effort', () => {
  it('recognizes DeepSeek V4 routes', () => {
    expect(isDeepSeekV4Model('cmc/deepseek/deepseek-v4-flash')).toBe(true)
    expect(isDeepSeekV4Model('deepseek/deepseek-v4-pro')).toBe(true)
    expect(isDeepSeekV4Model('nous/hermes-4')).toBe(false)
  })

  it('only exposes DeepSeek V4 native levels', () => {
    expect(reasoningEffortValuesForModel('deepseek-v4-flash')).toEqual(['none', 'low', 'high', 'max'])
    expect(defaultReasoningEffortForModel('deepseek-v4-flash')).toBe('high')
  })

  it('normalizes stale generic values to the active model default', () => {
    expect(normalizeReasoningEffort('medium', 'deepseek-v4-flash')).toBe('high')
    expect(normalizeReasoningEffort('max', 'deepseek-v4-flash')).toBe('max')
    expect(normalizeReasoningEffort(false, 'deepseek-v4-flash')).toBe('none')
    expect(normalizeReasoningEffort('', 'nous/hermes-4')).toBe('medium')
  })
})
