import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client.js'
import { createInterview } from '../api/interviews.js'
import Navbar from '../components/layout/Navbar.jsx'
import RoleSelector from '../components/interview/RoleSelector.jsx'
import Button from '../components/ui/Button.jsx'
import { ArrowLeftIcon, BookIcon, ChartIcon, TargetIcon } from '../components/ui/icons.jsx'
import { DEFAULT_DIFFICULTY, DEFAULT_QUESTION_COUNT, ROLES, getDefaultTopicsForRole } from '../data/interviewCatalog.js'

const BENEFITS = [
  {
    icon: TargetIcon,
    title: 'Realistic and adaptive',
    description: 'Questions adjust to your answers.',
  },
  {
    icon: ChartIcon,
    title: 'Focused practice',
    description: 'Covers the areas that matter for your role.',
  },
  {
    icon: BookIcon,
    title: 'Build confidence',
    description: 'Walk into your real interview prepared.',
  },
]

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
      // pacing are decided by the Technical Round itself from here on
      // (LangGraph adapts every question already; the backend still requires
      // these fields on creation, so they're derived from the role's own
      // catalog entry rather than exposed as controls).
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
    <div className="relative min-h-screen overflow-hidden bg-cream">
      <div
        aria-hidden="true"
        className="pointer-events-none fixed inset-0 -z-10 bg-cover bg-no-repeat opacity-90"
        style={{
          backgroundImage: 'url(/images/interview-setup-background.png)',
          backgroundPosition: 'left bottom',
        }}
      />
      <div
        aria-hidden="true"
        className="pointer-events-none fixed inset-0 -z-10 bg-gradient-to-b from-cream/40 via-transparent to-cream/60"
      />

      <Navbar />

      <main className="mx-auto max-w-7xl px-6 pb-24 pt-10">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-sm font-medium text-ink/70 transition-colors duration-200 hover:text-ink"
        >
          <ArrowLeftIcon className="h-4 w-4" />
          Back to home
        </Link>

        <div className="mt-10 grid gap-12 lg:grid-cols-[0.85fr_1.15fr] lg:items-start lg:gap-10">
          <div className="max-w-md lg:sticky lg:top-28">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent">
              Technical Round
            </p>
            <h1 className="mt-4 text-4xl font-semibold leading-[1.1] tracking-tight text-ink sm:text-5xl">
              Prepare for
              <br />
              <span className="text-accent">what&apos;s next.</span>
            </h1>
            <p className="mt-5 leading-relaxed text-muted">
              Choose the role you want to practice for. We&apos;ll run a real, adaptive
              technical round and adjust every question to how you answer.
            </p>

            <ul className="mt-9 flex flex-col gap-6">
              {BENEFITS.map((benefit) => (
                <li key={benefit.title} className="flex items-start gap-3.5">
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-accent">
                    <benefit.icon className="h-5 w-5" />
                  </span>
                  <div>
                    <p className="text-sm font-semibold text-ink">{benefit.title}</p>
                    <p className="mt-0.5 text-sm leading-relaxed text-muted">
                      {benefit.description}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          <div className="motion-safe:animate-rise rounded-3xl border border-line/70 bg-cream-soft/80 p-6 shadow-xl shadow-ink/5 backdrop-blur-sm sm:p-8">
            <div className="border-b border-line/70 pb-5">
              <h2 className="text-xl font-semibold text-ink sm:text-2xl">Technical Round</h2>
              <p className="mt-1.5 text-sm leading-relaxed text-muted">
                Select your role — everything else about the interview is handled for you.
              </p>
            </div>

            <section className="py-7">
              <h3 className="text-base font-semibold text-ink">Select your role</h3>
              <p className="mt-0.5 text-sm text-muted">Choose the role you want to practice for.</p>
              <div className="mt-4">
                <RoleSelector roles={ROLES} value={roleId} onChange={handleRoleChange} />
              </div>
            </section>

            <div className="pt-1">
              <Button
                onClick={handleStart}
                disabled={isSubmitting}
                aria-busy={isSubmitting}
                variant="inverse"
                withArrow={!isSubmitting}
                className="w-full justify-center"
              >
                {isSubmitting ? 'Starting your Technical Round…' : 'Start Technical Round'}
              </Button>
              {errorMessage && (
                <p role="alert" aria-live="assertive" className="mt-3 text-center text-sm text-error">
                  {errorMessage}
                </p>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

export default InterviewNew
