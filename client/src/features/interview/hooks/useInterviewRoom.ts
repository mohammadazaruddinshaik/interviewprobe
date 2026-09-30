import { useCallback, useEffect, useReducer, useRef, useState } from 'react'
import { ApiError } from '@/lib/api'
import { getCurrentUser } from '@/lib/auth'
import { completeInterview, getInterview, submitAnswer } from '../api/interviewRoomApi'
import { classifyAnswerError, classifyLoadError } from '../lib/errors'
import { attemptFor, clearAttempt, loadAttempt, saveAttempt, validateAnswer } from '../lib/idempotency'
import type { InterviewState, SubmitAnswerResponse, TranscriptEntry } from '../types/interview'
import { roomReducer, type RoomState } from './roomReducer'

type LoadOutcome = { ok: true; interview: InterviewState; userName: string | null } | { ok: false; phase: 'notFound' | 'unauthenticated' | 'loadError' }

// Shared in-flight load per interview so StrictMode's double effect doesn't duplicate the request.
const loads = new Map<string, Promise<LoadOutcome>>()

function dedupe<T>(map: Map<string, Promise<T>>, id: string, make: () => Promise<T>): Promise<T> {
  let pending = map.get(id)
  if (!pending) {
    pending = make().finally(() => map.delete(id))
    map.set(id, pending)
  }
  return pending
}

const loadInterview = (id: string) =>
  dedupe(loads, id, async (): Promise<LoadOutcome> => {
    try {
      const [interview, user] = await Promise.all([getInterview(id), getCurrentUser().catch(() => null)])
      return { ok: true, interview, userName: user?.name ?? null }
    } catch (error) {
      return { ok: false, phase: classifyLoadError(error) }
    }
  })

const NOT_AUTHENTICATED = 'unauthenticated' as const

/** The interview room's state machine: server state is authoritative; the draft, attempt and transcript are local. */
export function useInterviewRoom(interviewId: string) {
  const [state, dispatch] = useReducer(roomReducer, { phase: 'loading' } as RoomState)
  const [userName, setUserName] = useState<string | null>(null)
  const stateRef = useRef(state)
  useEffect(() => {
    stateRef.current = state // handlers read the latest committed state
  })
  const submitGuard = useRef(false) // synchronous duplicate-click guard

  // Turn a server snapshot into the right phase. Server wins over local state.
  const applyServerState = useCallback((interview: InterviewState, notice?: string) => {
    if (interview.status === 'COMPLETED') {
      clearAttempt(interviewId)
      dispatch({ type: 'ENDED' })
    } else if (interview.status === 'CREATED') dispatch({ type: 'PHASE', phase: 'notStarted' })
    else if (interview.status === 'FAILED') dispatch({ type: 'PHASE', phase: 'failed' })
    else if (interview.current_question) dispatch({ type: 'SYNC', interview, notice })
    else dispatch({ type: 'PHASE', phase: 'loadError' })
  }, [interviewId])

  // --- initial load / refresh: GET only, never /start -------------------------------------------------------
  useEffect(() => {
    let cancelled = false
    dispatch({ type: 'PHASE', phase: 'loading' })
    void loadInterview(interviewId).then((outcome) => {
      if (cancelled) return
      if (!outcome.ok) return dispatch({ type: 'PHASE', phase: outcome.phase })
      setUserName(outcome.userName)
      const { interview } = outcome
      if (interview.status === 'COMPLETED') {
        clearAttempt(interviewId)
        return dispatch({ type: 'ENDED' })
      }
      if (interview.status === 'CREATED') return dispatch({ type: 'PHASE', phase: 'notStarted' })
      if (interview.status === 'FAILED' || !interview.current_question) return dispatch({ type: 'PHASE', phase: interview.status === 'FAILED' ? 'failed' : 'loadError' })
      // An attempt stored for THIS question is surfaced as a retryable uncertain attempt (never auto-sent).
      const stored = loadAttempt(interviewId)
      const attempt = stored && stored.questionId === interview.current_question.id ? stored : null
      if (!attempt) clearAttempt(interviewId)
      dispatch({ type: 'LOADED', interview, question: interview.current_question, attempt })
    })
    return () => {
      cancelled = true
    }
  }, [interviewId])

  const resync = useCallback(
    async (notice?: string) => {
      try {
        applyServerState(await getInterview(interviewId), notice)
        return true
      } catch (error) {
        const phase = classifyLoadError(error)
        if (phase !== 'loadError') dispatch({ type: 'PHASE', phase })
        return false
      }
    },
    [applyServerState, interviewId],
  )

  // --- answering ----------------------------------------------------------------------------------------------
  const setDraft = useCallback((text: string) => dispatch({ type: 'DRAFT', text }), [])

  const submit = useCallback(async () => {
    const s = stateRef.current
    if (s.phase !== 'ready' || submitGuard.current || s.turn.status === 'submitting') return
    if (s.turn.status === 'rateLimited' && s.turn.until > Date.now()) return
    const valid = validateAnswer(s.draft)
    if (!valid.ok) return dispatch({ type: 'NOTICE', message: valid.message })

    // Same question + same trimmed answer => same attempt (same key); edited text => new logical answer.
    const attempt = attemptFor(s.attempt, s.question.id, valid.answer)
    saveAttempt(interviewId, attempt)
    submitGuard.current = true
    dispatch({ type: 'SUBMIT_START', attempt })

    try {
      const response: SubmitAnswerResponse = await submitAnswer(interviewId, attempt)
      clearAttempt(interviewId)
      if (response.action === 'END' || response.status === 'COMPLETED' || !response.question) {
        // The answer endpoint has already completed the interview: do NOT call /complete.
        dispatch({ type: 'ENDED' })
      } else {
        const entry: TranscriptEntry = {
          questionId: s.question.id,
          sequence: s.question.sequence,
          question: s.question.text,
          answer: attempt.answer,
        }
        dispatch({ type: 'ACCEPTED', question: response.question, entry })
        // Refresh server-derived progress/topics in the background; the accepted question is already shown.
        void getInterview(interviewId).then((fresh) => applyServerState(fresh)).catch(() => undefined)
      }
    } catch (error) {
      const failure = classifyAnswerError(error)
      switch (failure.kind) {
        case 'unauthenticated':
          dispatch({ type: 'PHASE', phase: NOT_AUTHENTICATED }) // the attempt stays stored for after sign-in
          break
        case 'notFound':
          dispatch({ type: 'PHASE', phase: 'notFound' })
          break
        case 'busy':
          dispatch({ type: 'TURN', turn: { status: 'busy', message: failure.message } })
          break
        case 'rateLimited':
          dispatch({ type: 'TURN', turn: { status: 'rateLimited', until: Date.now() + failure.retryAfterSeconds * 1000, message: failure.message } })
          break
        case 'unavailable':
        case 'uncertain':
          dispatch({ type: 'TURN', turn: { status: 'retryable', message: failure.message } }) // same attempt stays
          break
        case 'invalid':
          clearAttempt(interviewId)
          dispatch({ type: 'DROP_ATTEMPT' })
          dispatch({ type: 'NOTICE', message: failure.message })
          break
        case 'stale':
        case 'keyReused': {
          // Definitive rejection: re-sync from the server FIRST, then discard the attempt.
          const ok = await resync('The interview moved on, so we refreshed your question.')
          clearAttempt(interviewId)
          if (ok) dispatch({ type: 'DROP_ATTEMPT' })
          else dispatch({ type: 'TURN', turn: { status: 'retryable', message: 'We couldn’t refresh the interview. Please try again.' } })
          break
        }
      }
    } finally {
      submitGuard.current = false
    }
  }, [applyServerState, interviewId, resync])

  // --- explicit early exit --------------------------------------------------------------------------------------
  const openEnd = useCallback(() => dispatch({ type: 'END_FLOW', flow: { status: 'confirming' } }), [])
  const closeEnd = useCallback(() => {
    if (stateRef.current.phase === 'ready' && stateRef.current.endFlow.status !== 'ending') {
      dispatch({ type: 'END_FLOW', flow: { status: 'closed' } })
    }
  }, [])

  const confirmEnd = useCallback(async () => {
    const s = stateRef.current
    if (s.phase !== 'ready' || s.endFlow.status === 'ending' || submitGuard.current) return
    dispatch({ type: 'END_FLOW', flow: { status: 'ending' } })
    try {
      await completeInterview(interviewId)
      clearAttempt(interviewId)
      dispatch({ type: 'ENDED' })
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) return dispatch({ type: 'PHASE', phase: 'unauthenticated' })
      if (error instanceof ApiError && error.status === 404) return dispatch({ type: 'PHASE', phase: 'notFound' })
      if (error instanceof ApiError && error.status === 409) {
        dispatch({ type: 'END_FLOW', flow: { status: 'closed' } })
        await resync()
        return
      }
      dispatch({ type: 'END_FLOW', flow: { status: 'error', message: 'We couldn’t end the interview just now. Your interview is still open — please try again.' } })
    }
  }, [interviewId, resync])

  // --- completion: the result page owns evaluation. Replace (not push) so Back never returns to a dead room. ---
  const completed = state.phase === 'completed'
  useEffect(() => {
    if (completed) window.location.replace(`/app/interviews/${encodeURIComponent(interviewId)}/result`)
  }, [completed, interviewId])

  // Reconnect: when the browser comes back online or the tab is shown again, re-sync ONLY if nothing is uncertain.
  useEffect(() => {
    const onBack = () => {
      const s = stateRef.current
      if (document.visibilityState === 'hidden' || s.phase !== 'ready') return
      if (s.turn.status === 'answering' && !submitGuard.current) void resync()
    }
    window.addEventListener('online', onBack)
    document.addEventListener('visibilitychange', onBack)
    return () => {
      window.removeEventListener('online', onBack)
      document.removeEventListener('visibilitychange', onBack)
    }
  }, [resync])

  return { state, userName, setDraft, submit, openEnd, closeEnd, confirmEnd, reload: () => window.location.reload() }
}
