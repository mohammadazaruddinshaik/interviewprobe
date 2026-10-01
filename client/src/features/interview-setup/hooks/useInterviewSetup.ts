import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError } from '@/lib/api'
import { getCurrentUser, type AuthUser } from '@/lib/auth'
import {
  createInterview,
  fetchInterviewCatalog,
  startInterview,
  uploadResume,
  type InterviewCatalog,
} from '../api/interviewApi'
import { describeResumeFailure, describeSubmitFailure, isAlreadyStarted, RESUME_FAILED_MESSAGE } from '../lib/submitErrors'
import { fileKey, validateResumeFile } from '../lib/resumeFile'

type LoadState =
  | { status: 'loading' }
  | { status: 'ready'; catalog: InterviewCatalog; user: AuthUser }
  | { status: 'unauthenticated' }
  | { status: 'error' }

export type SubmitState =
  | { status: 'idle' }
  | { status: 'creating' }
  | { status: 'uploading' }
  | { status: 'starting' }
  | { status: 'error'; message: string }

async function loadCatalogAndUser(): Promise<LoadState> {
  try {
    // The catalog is public; /auth/me decides whether this screen may be used at all.
    const [catalog, user] = await Promise.all([fetchInterviewCatalog(), getCurrentUser()])
    if (!user) return { status: 'unauthenticated' }
    if (catalog.roles.length === 0) return { status: 'error' }
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
  // The only things the candidate controls: a role (defaults to the first in the catalog) and an optional resume.
  const [roleValue, setRoleValue] = useState<string | null>(null)
  const [submit, setSubmit] = useState<SubmitState>({ status: 'idle' })
  const [signedOut, setSignedOut] = useState(false)
  const [resume, setResume] = useState<File | null>(null)
  const [resumeError, setResumeError] = useState<string | null>(null)

  const submittingRef = useRef(false) // blocks duplicate clicks synchronously
  const createdRef = useRef<{ key: string; id: string } | null>(null) // a created interview survives a failed upload/start
  const uploadedRef = useRef<{ id: string; file: string } | null>(null) // a READY resume is never uploaded twice

  const applyLoad = useCallback((result: LoadState) => {
    setLoad(result)
    if (result.status === 'ready') setRoleValue((current) => current ?? result.catalog.roles[0].value)
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
  const role = catalog && roleValue ? catalog.roles.find((r) => r.value === roleValue) : undefined
  const busy = submit.status === 'creating' || submit.status === 'uploading' || submit.status === 'starting'

  const selectRole = useCallback(
    (value: string) => {
      if (submittingRef.current || !catalog?.roles.some((r) => r.value === value)) return
      setRoleValue(value)
      setSubmit((s) => (s.status === 'error' ? { status: 'idle' } : s))
    },
    [catalog],
  )

  const chooseResume = useCallback((file: File | null) => {
    if (submittingRef.current) return
    const problem = file ? validateResumeFile(file) : null
    setResumeError(problem)
    if (!problem) setResume(file)
    setSubmit((s) => (s.status === 'error' ? { status: 'idle' } : s))
  }, [])

  const canSubmit = !!role && !busy

  const submitSetup = useCallback(async () => {
    if (!role || submittingRef.current) return
    submittingRef.current = true
    const key = role.value
    try {
      let id = createdRef.current?.key === key ? createdRef.current.id : null
      if (!id) {
        setSubmit({ status: 'creating' })
        const created = await createInterview({ role: role.value })
        if (typeof created?.id !== 'string' || !created.id) throw new Error('Create response had no interview id.')
        id = created.id
        createdRef.current = { key, id }
      }
      // Optional resume: uploaded AFTER creation and BEFORE start (the planner reads it once, at start).
      if (resume && !(uploadedRef.current?.id === id && uploadedRef.current.file === fileKey(resume))) {
        setSubmit({ status: 'uploading' })
        let result
        try {
          result = await uploadResume(id, resume)
        } catch (error) {
          const failure = describeResumeFailure(error)
          if (failure.kind === 'unauthenticated') setSignedOut(true)
          else setSubmit({ status: 'error', message: failure.message })
          submittingRef.current = false
          return // never start after a failed upload
        }
        if (result.status !== 'READY') {
          setSubmit({ status: 'error', message: RESUME_FAILED_MESSAGE })
          submittingRef.current = false
          return
        }
        uploadedRef.current = { id, file: fileKey(resume) }
      }
      setSubmit({ status: 'starting' })
      try {
        await startInterview(id)
      } catch (error) {
        // A start whose response was lost may have succeeded server-side; the retry then sees the interview as
        // already started. The room fetches the authoritative state, so hand off instead of failing.
        if (!isAlreadyStarted(error)) throw error
      }
      window.location.assign(interviewDestination(id)) // only after the interview exists and was started
    } catch (error) {
      const failure = describeSubmitFailure(error)
      if (failure.kind === 'unauthenticated') setSignedOut(true)
      else setSubmit({ status: 'error', message: failure.message })
      submittingRef.current = false
    }
  }, [role, resume])

  return {
    status: signedOut ? ('unauthenticated' as const) : load.status,
    user: load.status === 'ready' ? load.user : null,
    catalog,
    role,
    submit,
    busy,
    canSubmit,
    retryLoad,
    selectRole,
    resume,
    resumeError,
    chooseResume,
    submitSetup,
  }
}
