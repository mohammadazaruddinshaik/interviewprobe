import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError } from '@/lib/api'
import { getCurrentUser, type AuthUser } from '@/lib/auth'
import {
  createInterview,
  fetchInterviewCatalog,
  startInterview,
  type CatalogRole,
  type InterviewCatalog,
} from '../api/interviewApi'
import { DEFAULT_DIFFICULTY, DEFAULT_QUESTION_LIMIT, DEFAULT_TOPIC_COUNT } from '../lib/copy'
import { describeSubmitFailure } from '../lib/submitErrors'

export interface SetupSelection {
  role: string
  difficulty: string
  topics: string[]
  questionLimit: number
}

type LoadState =
  | { status: 'loading' }
  | { status: 'ready'; catalog: InterviewCatalog; user: AuthUser }
  | { status: 'unauthenticated' }
  | { status: 'error' }

export type SubmitState =
  | { status: 'idle' }
  | { status: 'creating' }
  | { status: 'starting' }
  | { status: 'error'; message: string }

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value))

/** Only the first `count` topics of a role, never more than the role has. */
const defaultTopics = (role: CatalogRole) => role.topics.slice(0, DEFAULT_TOPIC_COUNT).map((t) => t.value)

function initialSelection(catalog: InterviewCatalog): SetupSelection {
  const role = catalog.roles[0]
  const difficulties = catalog.difficulties.map((d) => d.value)
  return {
    role: role.value,
    difficulty: difficulties.includes(DEFAULT_DIFFICULTY) ? DEFAULT_DIFFICULTY : difficulties[0],
    topics: defaultTopics(role),
    questionLimit: clamp(DEFAULT_QUESTION_LIMIT, catalog.question_limit.min, catalog.question_limit.max),
  }
}

async function loadCatalogAndUser(): Promise<LoadState> {
  try {
    // The catalog is public; /auth/me decides whether this screen may be used at all.
    const [catalog, user] = await Promise.all([fetchInterviewCatalog(), getCurrentUser()])
    if (!user) return { status: 'unauthenticated' }
    if (catalog.roles.length === 0 || catalog.difficulties.length === 0) return { status: 'error' }
    return { status: 'ready', catalog, user }
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return { status: 'unauthenticated' }
    return { status: 'error' }
  }
}

// One shared in-flight load so StrictMode's double effect doesn't fetch twice.
let inflight: Promise<LoadState> | null = null
const loadOnce = () => (inflight ??= loadCatalogAndUser().finally(() => (inflight = null)))

/** Where to go after a successful create + start. Temporary convention: the future interview room route. */
export const interviewDestination = (id: string) => `/app/interviews/${encodeURIComponent(id)}`

export function useInterviewSetup() {
  const [load, setLoad] = useState<LoadState>({ status: 'loading' })
  const [selection, setSelection] = useState<SetupSelection | null>(null)
  const [submit, setSubmit] = useState<SubmitState>({ status: 'idle' })
  const [signedOut, setSignedOut] = useState(false)

  const submittingRef = useRef(false) // blocks duplicate clicks synchronously
  const createdRef = useRef<{ key: string; id: string } | null>(null) // a created interview survives a failed start

  const applyLoad = useCallback((result: LoadState) => {
    setLoad(result)
    if (result.status === 'ready') setSelection((current) => current ?? initialSelection(result.catalog))
  }, [])

  useEffect(() => {
    let cancelled = false
    void loadOnce().then((result) => {
      if (!cancelled) applyLoad(result)
    })
    return () => {
      cancelled = true
    }
  }, [applyLoad])

  const retryLoad = useCallback(() => {
    setLoad({ status: 'loading' })
    void loadOnce().then(applyLoad)
  }, [applyLoad])

  const catalog = load.status === 'ready' ? load.catalog : null
  const role = catalog && selection ? catalog.roles.find((r) => r.value === selection.role) : undefined
  const topicCap = catalog && role ? Math.min(catalog.topic_limit.max, role.topics.length) : 0
  const busy = submit.status === 'creating' || submit.status === 'starting'

  const update = useCallback((change: (current: SetupSelection) => SetupSelection) => {
    if (submittingRef.current) return
    setSelection((current) => (current ? change(current) : current))
    setSubmit((s) => (s.status === 'error' ? { status: 'idle' } : s))
  }, [])

  const selectRole = useCallback(
    (value: string) => {
      if (!catalog) return
      const next = catalog.roles.find((r) => r.value === value)
      if (!next) return
      update((current) => {
        // Keep only topics valid for the new role; if none survive, fall back to its first topics.
        const valid = new Set(next.topics.map((t) => t.value))
        const kept = current.topics.filter((t) => valid.has(t)).slice(0, catalog.topic_limit.max)
        return { ...current, role: value, topics: kept.length > 0 ? kept : defaultTopics(next) }
      })
    },
    [catalog, update],
  )

  const toggleTopic = useCallback(
    (value: string) => {
      update((current) => {
        if (current.topics.includes(value)) return { ...current, topics: current.topics.filter((t) => t !== value) }
        if (current.topics.length >= topicCap || !role?.topics.some((t) => t.value === value)) return current
        return { ...current, topics: [...current.topics, value] }
      })
    },
    [role, topicCap, update],
  )

  const selectDifficulty = useCallback((difficulty: string) => update((c) => ({ ...c, difficulty })), [update])
  const selectQuestionLimit = useCallback((questionLimit: number) => update((c) => ({ ...c, questionLimit })), [update])

  const canSubmit = !!catalog && !!selection && selection.topics.length >= catalog.topic_limit.min && !busy

  const submitSetup = useCallback(async () => {
    if (!catalog || !selection || submittingRef.current) return
    if (selection.topics.length < catalog.topic_limit.min) return
    submittingRef.current = true
    const key = JSON.stringify(selection)
    try {
      let id = createdRef.current?.key === key ? createdRef.current.id : null
      if (!id) {
        setSubmit({ status: 'creating' })
        id = (
          await createInterview({
            role: selection.role,
            difficulty: selection.difficulty,
            topics: selection.topics,
            question_limit: selection.questionLimit,
          })
        ).id
        createdRef.current = { key, id }
      }
      setSubmit({ status: 'starting' })
      await startInterview(id)
      window.location.assign(interviewDestination(id)) // only after BOTH calls succeeded
    } catch (error) {
      const failure = describeSubmitFailure(error)
      if (failure.kind === 'unauthenticated') setSignedOut(true)
      else setSubmit({ status: 'error', message: failure.message })
      submittingRef.current = false
    }
  }, [catalog, selection])

  return {
    status: signedOut ? ('unauthenticated' as const) : load.status,
    user: load.status === 'ready' ? load.user : null,
    catalog,
    selection,
    role,
    topicCap,
    submit,
    busy,
    canSubmit,
    retryLoad,
    selectRole,
    selectDifficulty,
    toggleTopic,
    selectQuestionLimit,
    submitSetup,
  }
}
