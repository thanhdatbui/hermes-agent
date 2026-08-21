import { QueryClient } from '@tanstack/react-query'
import { act, cleanup, render, waitFor } from '@testing-library/react'
import { useEffect, useRef } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { ClientSessionState } from '@/app/types'
import { createClientSessionState } from '@/lib/chat-runtime'
import type { RpcEvent } from '@/types/hermes'

import { useMessageStream } from './index'

const SID = 'session-lifecycle'
let handleEvent: ((event: RpcEvent) => void) | null = null
let states = new Map<string, ClientSessionState>()

function Harness() {
  const activeSessionIdRef = useRef<string | null>(SID)
  const sessionStateByRuntimeIdRef = useRef(states)
  const queryClientRef = useRef(new QueryClient())

  const stream = useMessageStream({
    activeSessionIdRef,
    hydrateFromStoredSession: vi.fn(async () => undefined),
    queryClient: queryClientRef.current,
    refreshHermesConfig: vi.fn(async () => undefined),
    refreshSessions: vi.fn(async () => undefined),
    sessionStateByRuntimeIdRef,
    updateSessionState: (sessionId, updater) => {
      const current = states.get(sessionId) ?? createClientSessionState()
      const next = updater(current)
      states.set(sessionId, next)

      return next
    }
  })

  useEffect(() => {
    handleEvent = stream.handleGatewayEvent
  }, [stream.handleGatewayEvent])

  return null
}

async function mountStream() {
  render(<Harness />)
  await waitFor(() => expect(handleEvent).not.toBeNull())
}

function emit(type: RpcEvent['type'], payload: RpcEvent['payload'] = {}) {
  act(() => handleEvent!({ payload, session_id: SID, type }))
}

describe('useMessageStream turn terminal lifecycle', () => {
  beforeEach(() => {
    handleEvent = null
    states = new Map()
  })

  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('settles a streamed response after delta and complete', async () => {
    await mountStream()

    emit('message.start')
    emit('message.delta', { text: 'DeepSeek reply' })
    emit('message.complete', { text: 'DeepSeek reply', status: 'complete' })

    const state = states.get(SID)!
    expect(state.messages.at(-1)?.role).toBe('assistant')
    expect(state.messages.at(-1)?.pending).toBe(false)
    expect(state.messages.at(-1)?.error).toBeUndefined()
    expect(state.busy).toBe(false)
    expect(state.awaitingResponse).toBe(false)
  })

  it('settles an agent/provider error without requiring a delta', async () => {
    await mountStream()

    emit('message.start')
    emit('error', { message: '9Router provider unavailable' })

    const state = states.get(SID)!
    expect(state.messages.at(-1)?.role).toBe('assistant')
    expect(state.messages.at(-1)?.error).toBe('9Router provider unavailable')
    expect(state.messages.at(-1)?.pending).toBe(false)
    expect(state.busy).toBe(false)
    expect(state.awaitingResponse).toBe(false)
  })
})
