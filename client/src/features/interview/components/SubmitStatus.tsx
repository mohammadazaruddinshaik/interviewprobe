import type { Turn } from '../hooks/roomReducer'

interface SubmitStatusProps {
  turn: Turn
  secondsLeft: number
  hasAttempt: boolean
  onRetry: () => void
}

/** Announces answer-submission problems. Retrying reuses the same key, so it can't send a duplicate. */
function SubmitStatus({ turn, secondsLeft, hasAttempt, onRetry }: SubmitStatusProps) {
  let message: string | null = null
  let detail: string | null = null
  let canRetry = false

  if (turn.status === 'answering') message = turn.notice
  else if (turn.status === 'retryable' || turn.status === 'busy' || turn.status === 'rateLimited') {
    message = turn.message
    canRetry = true
    detail = hasAttempt ? 'Retrying is safe: your answer won’t be counted twice.' : null
    if (turn.status === 'rateLimited') detail = secondsLeft > 0 ? `Please wait ${secondsLeft}s before trying again.` : 'You can try again now.'
  }

  return (
    <div aria-live="polite" className="min-h-[22px]">
      {message && (
        <div role="alert" className="rounded-xl border border-orange/30 bg-orange/[0.06] px-3.5 py-3">
          <p className="text-[13.5px] font-medium text-deep">{message}</p>
          {detail && <p className="mt-0.5 text-[12.5px] text-ink/60">{detail}</p>}
          {canRetry && (
            <button
              type="button"
              onClick={onRetry}
              disabled={turn.status === 'rateLimited' && secondsLeft > 0}
              className="mt-2 rounded-lg border border-forest/30 bg-cream px-3 py-1.5 text-[13px] font-semibold text-forest outline-offset-2 transition-colors hover:bg-forest/[0.05] focus-visible:outline-[3px] focus-visible:outline-yellow disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:transition-none"
            >
              {turn.status === 'rateLimited' && secondsLeft > 0 ? `Retry in ${secondsLeft}s` : 'Retry sending'}
            </button>
          )}
        </div>
      )}
    </div>
  )
}

export default SubmitStatus
