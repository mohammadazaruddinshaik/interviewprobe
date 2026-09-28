import { Clock, Moon, PhoneOff, Sun } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import BrandLogo from '../../ui/BrandLogo.jsx'
import { useTheme } from '../../../hooks/useTheme.js'

// Contextual section labels only — "Interview" is the only one with a
// real destination (this page itself). Progress/Feedback/Resources have
// no real pages anywhere in the app (see App.jsx's router), so they're
// rendered as inert, muted labels rather than becoming fake routes or
// dead links. There is no user/profile control because the product has
// no authentication.
const CONTEXT_LABELS = ['Progress', 'Feedback', 'Resources']

// The interview's real hard maximum — enforced server-side (separately
// from this frontend task); this is the display's one source of truth for
// what "full time" means, not an invented value.
const INTERVIEW_DURATION_SECONDS = 45 * 60
// The last stretch where the display quietly steps up from muted to a
// warmer tone — never a flashing/alarming countdown, just a touch more
// present.
const LOW_TIME_THRESHOLD_SECONDS = 5 * 60

function formatRemaining(totalSeconds) {
  const clamped = Math.max(0, totalSeconds)
  const minutes = Math.floor(clamped / 60)
  const seconds = clamped % 60
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}

// A real, running countdown against the product's actual 45-minute cap —
// measured from when this room mounted. GET /interviews/{id} exposes no
// authoritative session-start timestamp, so there is nothing server-side
// to anchor to yet; this resets on reload, the same honest scope as the
// local transcript in Interview.jsx. The backend's own hard-limit
// enforcement is separate, later work — this display doesn't invent one.
function useRemainingSeconds() {
  const [remaining, setRemaining] = useState(INTERVIEW_DURATION_SECONDS)

  useEffect(() => {
    const startedAt = Date.now()
    const id = setInterval(() => {
      const elapsed = Math.floor((Date.now() - startedAt) / 1000)
      setRemaining(Math.max(0, INTERVIEW_DURATION_SECONDS - elapsed))
    }, 1000)
    return () => clearInterval(id)
  }, [])

  return remaining
}

// Ending is irreversible (the session becomes COMPLETED and the current
// draft answer is not submitted), so the first click only opens a small
// confirmation; the second, explicit click calls the existing completion
// flow. Nothing here ever completes the interview on render.
function EndInterviewControl({ onEndInterview, ending, disabled }) {
  const [confirming, setConfirming] = useState(false)
  const confirmRef = useRef(null)

  useEffect(() => {
    if (!confirming) return undefined
    confirmRef.current?.focus()
    function handleKeyDown(event) {
      if (event.key === 'Escape') setConfirming(false)
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [confirming])

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setConfirming((open) => !open)}
        disabled={disabled || ending}
        aria-expanded={confirming}
        aria-controls="end-interview-confirm"
        className="flex items-center gap-1.5 whitespace-nowrap rounded-full bg-danger px-3.5 py-2 text-sm font-medium text-white shadow-glass-sm transition-colors duration-200 hover:bg-danger/90 disabled:cursor-not-allowed disabled:opacity-60 sm:px-4"
      >
        <PhoneOff className="h-4 w-4" strokeWidth={1.75} aria-hidden="true" />
        {ending ? 'Ending…' : 'End Interview'}
      </button>

      {confirming && (
        <div
          id="end-interview-confirm"
          role="dialog"
          aria-label="Confirm ending the interview"
          className="absolute right-0 top-full z-20 mt-2 w-64 rounded-2xl border border-glass/70 bg-surface p-4 shadow-glass"
        >
          <p className="text-sm font-semibold text-ink">End this interview now?</p>
          <p className="mt-1 text-xs leading-relaxed text-muted">
            Your current answer won&apos;t be submitted. You&apos;ll go straight to your results.
          </p>
          <div className="mt-3 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setConfirming(false)}
              className="rounded-full px-3 py-1.5 text-xs font-medium text-muted transition-colors duration-200 hover:text-ink"
            >
              Keep going
            </button>
            <button
              ref={confirmRef}
              type="button"
              onClick={() => {
                setConfirming(false)
                onEndInterview()
              }}
              className="rounded-full bg-danger px-3 py-1.5 text-xs font-medium text-white transition-colors duration-200 hover:bg-danger/90"
            >
              End interview
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function InterviewNavbar({ onEndInterview, ending = false, endDisabled = false }) {
  const remainingSeconds = useRemainingSeconds()
  const isLowTime = remainingSeconds <= LOW_TIME_THRESHOLD_SECONDS
  const { theme, toggleTheme } = useTheme()

  return (
    <header className="shrink-0 px-4 pt-3 sm:px-6 lg:px-6 lg:pt-4">
      <div className="flex h-12 items-center justify-between gap-3 sm:h-14">
        <a href="/" className="flex shrink-0 items-center">
          <BrandLogo collapse />
        </a>

        <nav
          aria-label="Interview sections"
          className="hidden items-center gap-1 rounded-full border border-line bg-glass/50 p-1 lg:flex"
        >
          <span
            aria-current="page"
            className="rounded-full bg-glass px-5 py-2 text-sm font-medium text-primary shadow-glass-sm"
          >
            Interview
          </span>
          {CONTEXT_LABELS.map((label) => (
            <span key={label} aria-disabled="true" className="cursor-default px-5 py-2 text-sm text-muted/70">
              {label}
            </span>
          ))}
        </nav>

        <div className="flex shrink-0 items-center gap-2">
          <span
            className={`hidden items-center gap-2 whitespace-nowrap rounded-full border px-3.5 py-2 text-sm font-semibold tabular-nums sm:flex ${
              isLowTime ? 'border-warning/40 bg-warning/10 text-warning' : 'border-line bg-glass/60 text-ink'
            }`}
            aria-label={`${formatRemaining(remainingSeconds)} remaining`}
          >
            <Clock className="h-4 w-4" strokeWidth={1.75} aria-hidden="true" />
            {formatRemaining(remainingSeconds)}
          </span>
          <button
            type="button"
            onClick={toggleTheme}
            aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-line bg-glass/60 text-ink/70 transition-colors duration-200 hover:bg-glass hover:text-ink"
          >
            {theme === 'dark' ? <Sun className="h-4 w-4" strokeWidth={1.75} /> : <Moon className="h-4 w-4" strokeWidth={1.75} />}
          </button>
          {onEndInterview && (
            <EndInterviewControl onEndInterview={onEndInterview} ending={ending} disabled={endDisabled} />
          )}
        </div>
      </div>
    </header>
  )
}

export default InterviewNavbar
