import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client.js'
import { createInterview } from '../api/interviews.js'
import InterviewPreview from '../components/setup/InterviewPreview.jsx'
import InterviewStepper from '../components/setup/InterviewStepper.jsx'
import ResumeUpload from '../components/setup/ResumeUpload.jsx'
import RoleSelector from '../components/setup/RoleSelector.jsx'
import SetupFeatureList from '../components/setup/SetupFeatureList.jsx'
import SetupHeader from '../components/setup/SetupHeader.jsx'
import SetupNavbar from '../components/setup/SetupNavbar.jsx'
import SetupShell from '../components/setup/SetupShell.jsx'
import Button from '../components/ui/Button.jsx'
import { InlineProbeLoader } from '../components/ui/InterviewProbeLoader.jsx'
import { DEFAULT_DIFFICULTY, DEFAULT_QUESTION_COUNT, ROLES, getDefaultTopicsForRole } from '../data/interviewCatalog.js'

function InterviewNew() {
  const navigate = useNavigate()
  const [roleId, setRoleId] = useState(ROLES[0].id)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState(null)

  // An interview session created early, ONLY because the candidate
  // actually picked a resume file to upload (POST /interviews/{id}/resume
  // needs a real session to attach to) — never created just by landing on
  // this page. Start Interview reuses it instead of creating a second
  // session when one is already reserved this way. A ref (not state):
  // reading it never needs to trigger a render, and `ResumeUpload` reads
  // it through a stable async callback rather than a prop that goes stale.
  const reservedSessionIdRef = useRef(null)

  const role = ROLES.find((r) => r.id === roleId) ?? ROLES[0]

  function handleRoleChange(nextRoleId) {
    setRoleId(nextRoleId)
    setErrorMessage(null)
    // A session reserved for a resume upload was created with the
    // PREVIOUS role's topics — switching roles invalidates that
    // selection, so the reservation (and, via ResumeUpload's `key` below,
    // its own upload state) resets to a clean slate rather than silently
    // starting the new role's interview from a stale, wrong-topic session.
    reservedSessionIdRef.current = null
  }

  // Passed to ResumeUpload as `ensureSessionId` — called only when the
  // candidate actually picks a file. Reuses the existing reservation if
  // one already exists for the current role (e.g. replacing a resume),
  // otherwise creates a real session right now with the currently
  // selected role's own catalog topics, exactly as handleStart would.
  async function ensureSessionId() {
    if (reservedSessionIdRef.current) return reservedSessionIdRef.current
    const interview = await createInterview({
      role: roleId,
      difficulty: DEFAULT_DIFFICULTY,
      topics: getDefaultTopicsForRole(role),
      questionLimit: DEFAULT_QUESTION_COUNT,
    })
    reservedSessionIdRef.current = interview.id
    return interview.id
  }

  async function handleStart() {
    if (isSubmitting) return
    setIsSubmitting(true)
    setErrorMessage(null)
    try {
      // A resume upload may have already created this exact session
      // (with these exact role/difficulty/topics) — reuse it rather than
      // creating a second, resume-less duplicate.
      if (reservedSessionIdRef.current) {
        navigate(`/interview/${reservedSessionIdRef.current}`)
        return
      }
      // Only the role is a candidate choice — difficulty, topic breadth, and
      // pacing are decided by the interview itself from here on (the
      // adaptive engine adjusts every question already; the backend still
      // requires these fields on creation, so they're derived from the
      // role's own catalog entry rather than exposed as controls).
      const interview = await createInterview({
        role: roleId,
        difficulty: DEFAULT_DIFFICULTY,
        topics: getDefaultTopicsForRole(role),
        questionLimit: DEFAULT_QUESTION_COUNT,
      })
      navigate(`/interview/${interview.id}`)
    } catch (error) {
      setErrorMessage(
        error instanceof ApiError ? error.message : 'Something went wrong while creating your interview.',
      )
      setIsSubmitting(false)
    }
  }

  return (
    <div className="relative overflow-x-hidden text-ink">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -left-16 -top-16 h-64 w-64 rounded-full bg-primary-light/50 opacity-70 blur-3xl sm:-left-24 sm:-top-24 sm:h-96 sm:w-96"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -bottom-8 -right-8 h-56 w-56 opacity-[0.35] sm:h-72 sm:w-72"
        style={{
          backgroundImage: 'radial-gradient(var(--color-primary) 1px, transparent 1px)',
          backgroundSize: '18px 18px',
          maskImage: 'radial-gradient(circle at bottom right, black 0%, transparent 70%)',
          WebkitMaskImage: 'radial-gradient(circle at bottom right, black 0%, transparent 70%)',
        }}
      />
      <div className="relative px-3 py-2.5 sm:px-5 sm:py-3 lg:flex lg:min-h-svh lg:flex-col lg:px-6 lg:py-4">
        <SetupShell>
          <SetupNavbar />

          <main className="px-4 pb-4 pt-3 sm:px-6 lg:flex lg:flex-1 lg:flex-col lg:px-8 lg:pb-6 lg:pt-4">
            <SetupHeader />

            <div className="mt-4 grid grid-cols-1 gap-5 lg:flex-1 lg:grid-cols-[minmax(0,1fr)_280px] xl:grid-cols-[minmax(0,1fr)_380px] 2xl:grid-cols-[minmax(0,1fr)_440px]">
              <div className="flex min-w-0 flex-col justify-between rounded-[22px] border border-glass/70 bg-glass/60 p-3 shadow-glass-sm sm:p-4 lg:p-5">
                <div className="flex flex-col lg:flex-1">
                  <InterviewStepper activeStep={1} />

                  <p className="mb-1 mt-4 text-xs font-semibold uppercase tracking-wide text-muted">Select Role</p>

                  <RoleSelector roles={ROLES} value={roleId} onChange={handleRoleChange} />

                  {/* `key={roleId}`: a role change invalidates any reservation
                      made under the previous role (see handleRoleChange), so
                      this remounts to a clean idle state right along with it —
                      never left showing a resume that belongs to a different
                      role's now-abandoned session. */}
                  <div className="mt-4">
                    <ResumeUpload key={roleId} ensureSessionId={ensureSessionId} />
                  </div>
                </div>

                <div className="mt-4">
                  <Button
                    onClick={handleStart}
                    disabled={isSubmitting}
                    aria-busy={isSubmitting}
                    variant="primary"
                    withArrow={!isSubmitting}
                    className="w-full justify-center bg-gradient-to-r from-primary to-accent-2 py-3 text-sm"
                  >
                    {isSubmitting ? <InlineProbeLoader label="Starting your interview…" /> : 'Start Interview'}
                  </Button>
                  {errorMessage && (
                    <p role="alert" aria-live="assertive" className="mt-2 text-center text-xs text-error">
                      {errorMessage}
                    </p>
                  )}
                </div>
              </div>

              <div className="flex min-w-0 flex-col gap-4">
                <InterviewPreview />
                <SetupFeatureList />
              </div>
            </div>
          </main>
        </SetupShell>
      </div>
    </div>
  )
}

export default InterviewNew
