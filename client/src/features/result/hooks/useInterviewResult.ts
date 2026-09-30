import { useCallback, useEffect, useReducer, useRef, useState } from 'react'
import { getInterview } from '@/features/interview/api/interviewRoomApi'
import { getCurrentUser } from '@/lib/auth'
import { fetchInterviewResult } from '../api/resultApi'
import { classifyResultError, isValidResult } from '../lib/resultErrors'
import { resultReducer, type ResultState } from './resultReducer'

/** Show the skeleton this long, then switch to the "preparing your evaluation" message. */
export const SLOW_AFTER_MS = 600
/** EVALUATION_BUSY is retried automatically but only for a bounded window (~30s), never forever. */
export const BUSY_RETRY_MS = 3000
export const BUSY_MAX_ATTEMPTS = 10

type Outcome = { state: ResultState; userName: string | null }

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

async function notCompletedState(id: string): Promise<ResultState> {
  try {
    return { phase: 'notCompleted', status: (await getInterview(id)).status }
  } catch {
    return { phase: 'notCompleted', status: null }
  }
}

async function loadResult(id: string): Promise<Outcome> {
  const userPromise = getCurrentUser().then((u) => u?.name ?? null, () => null)
  for (let attempt = 1; ; attempt += 1) {
    try {
      const result = await fetchInterviewResult(id)
      if (!isValidResult(result)) return { state: { phase: 'failed', reason: 'load' }, userName: null }
      return { state: { phase: 'ready', result }, userName: await userPromise }
    } catch (error) {
      const failure = classifyResultError(error)
      switch (failure.kind) {
        case 'busy':
          if (attempt >= BUSY_MAX_ATTEMPTS) return { state: { phase: 'failed', reason: 'evaluation' }, userName: null }
          await wait(BUSY_RETRY_MS) // idempotent re-request of the same result
          continue
        case 'notCompleted':
          return { state: await notCompletedState(id), userName: await userPromise }
        case 'evaluationFailed':
          return { state: { phase: 'failed', reason: 'evaluation' }, userName: null }
        case 'notFound':
        case 'unauthenticated':
          return { state: { phase: failure.kind }, userName: null }
        default:
          return { state: { phase: 'failed', reason: 'load' }, userName: null }
      }
    }
  }
}

// One shared in-flight load per interview: StrictMode's double effect must not send two /result requests
// (the first request may trigger a one-off LLM evaluation on the server).
const inflight = new Map<string, Promise<Outcome>>()
function loadOnce(id: string) {
  let pending = inflight.get(id)
  if (!pending) {
    pending = loadResult(id).finally(() => inflight.delete(id))
    inflight.set(id, pending)
  }
  return pending
}

export function useInterviewResult(interviewId: string) {
  const [state, dispatch] = useReducer(resultReducer, { phase: 'loading' } as ResultState)
  const [userName, setUserName] = useState<string | null>(null)
  const mounted = useRef(true)

  const run = useCallback(() => {
    dispatch({ type: 'RESET' })
    const slow = window.setTimeout(() => dispatch({ type: 'SLOW' }), SLOW_AFTER_MS)
    void loadOnce(interviewId).then((outcome) => {
      window.clearTimeout(slow)
      if (!mounted.current) return
      if (outcome.userName) setUserName(outcome.userName)
      dispatch({ type: 'OUTCOME', state: outcome.state })
    })
    return () => window.clearTimeout(slow)
  }, [interviewId])

  useEffect(() => {
    mounted.current = true
    const cleanup = run()
    return () => {
      mounted.current = false
      cleanup()
    }
  }, [run])

  return { state, userName, retry: run }
}
