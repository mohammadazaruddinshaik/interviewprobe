import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client.js'
import { createInterview } from '../api/interviews.js'
import InterviewPreview from '../components/setup/InterviewPreview.jsx'
import InterviewStepper from '../components/setup/InterviewStepper.jsx'
import RoleSelector from '../components/setup/RoleSelector.jsx'
import SetupFeatureList from '../components/setup/SetupFeatureList.jsx'
import SetupHeader from '../components/setup/SetupHeader.jsx'
import SetupNavbar from '../components/setup/SetupNavbar.jsx'
import SetupShell from '../components/setup/SetupShell.jsx'
import Button from '../components/ui/Button.jsx'
import { DEFAULT_DIFFICULTY, DEFAULT_QUESTION_COUNT, ROLES, getDefaultTopicsForRole } from '../data/interviewCatalog.js'

function InterviewNew() {
  const navigate = useNavigate()
  const [roleId, setRoleId] = useState(ROLES[0].id)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState(null)

  const role = ROLES.find((r) => r.id === roleId) ?? ROLES[0]

  function handleRoleChange(nextRoleId) {
    setRoleId(nextRoleId)
    setErrorMessage(null)
  }

  async function handleStart() {
    if (isSubmitting) return
    setIsSubmitting(true)
    setErrorMessage(null)
    try {
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
      <div className="relative px-3 py-2.5 sm:px-5 sm:py-3 lg:px-6 lg:py-4">
        <SetupShell>
          <SetupNavbar />

          <main className="px-4 pb-4 pt-3 sm:px-6 lg:px-8 lg:pb-5 lg:pt-4">
            <SetupHeader />

            <div className="mt-4 grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1fr)_280px] xl:grid-cols-[minmax(0,1fr)_340px]">
              <div className="flex min-w-0 flex-col justify-between rounded-[22px] border border-glass/70 bg-glass/60 p-3 shadow-glass-sm sm:p-4 lg:p-5">
                <div>
                  <InterviewStepper activeStep={1} />

                  <p className="mb-1 mt-4 text-xs font-semibold uppercase tracking-wide text-muted">Select Role</p>

                  <RoleSelector roles={ROLES} value={roleId} onChange={handleRoleChange} />
                </div>

                <div className="mt-4">
                  <Button
                    onClick={handleStart}
                    disabled={isSubmitting}
                    aria-busy={isSubmitting}
                    variant="primary"
                    withArrow={!isSubmitting}
                    className="w-full justify-center bg-gradient-to-br from-[#94a1f8] to-primary py-3 text-sm shadow-[0_10px_28px_-8px_rgba(91,111,245,0.55)]"
                  >
                    {isSubmitting ? 'Starting your interview…' : 'Start Interview'}
                  </Button>
                  {errorMessage && (
                    <p role="alert" aria-live="assertive" className="mt-2 text-center text-xs text-error">
                      {errorMessage}
                    </p>
                  )}
                </div>
              </div>

              <div className="flex min-w-0 flex-col justify-between gap-3">
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
