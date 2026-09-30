import type { KeyboardEvent } from 'react'
import { MAX_ANSWER_LENGTH } from '../lib/idempotency'
import { sendButtonState } from '../lib/sendState'
import type { AnswerAttempt } from '../types/interview'
import type { Turn } from '../hooks/roomReducer'
import SendButton from './SendButton'
import SubmitStatus from './SubmitStatus'

interface AnswerComposerProps {
  draft: string
  attempt: AnswerAttempt | null
  turn: Turn
  secondsLeft: number
  onChange: (text: string) => void
  onSubmit: () => void
}

function AnswerComposer({ draft, attempt, turn, secondsLeft, onChange, onSubmit }: AnswerComposerProps) {
  const button = sendButtonState(draft, attempt, turn, secondsLeft)
  const length = draft.length
  const over = draft.trim().length > MAX_ANSWER_LENGTH

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
      event.preventDefault()
      if (!button.disabled && !button.busy) onSubmit()
    }
  }

  return (
    <section data-room="composer" aria-label="Your answer" className="flex flex-col gap-3">
      <label htmlFor="room-answer" className="text-[14px] font-semibold text-deep">
        Your answer
      </label>
      <textarea
        id="room-answer"
        value={draft}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={onKeyDown}
        readOnly={turn.status === 'submitting'}
        rows={8}
        aria-describedby="room-answer-help"
        aria-invalid={over || undefined}
        placeholder="Type your answer here…"
        className="min-h-[200px] w-full resize-y rounded-2xl border border-ink/15 bg-white/70 px-4 py-3.5 text-[15.5px] leading-[1.55] text-ink outline-offset-2 transition-colors duration-200 placeholder:text-ink/35 focus-visible:border-forest focus-visible:outline-[3px] focus-visible:outline-yellow read-only:bg-forest/[0.03] motion-reduce:transition-none"
      />
      <div className="flex items-center justify-between gap-3 text-[12.5px]">
        <span id="room-answer-help" className="text-ink/55">
          Ctrl/⌘ + Enter to send
        </span>
        <span className={over ? 'font-semibold text-orange' : 'text-ink/55'} aria-live="polite">
          {length.toLocaleString()} / {MAX_ANSWER_LENGTH.toLocaleString()}
        </span>
      </div>

      <SubmitStatus turn={turn} secondsLeft={secondsLeft} hasAttempt={!!attempt} onRetry={onSubmit} />

      {/* Desktop/tablet action; below lg the fixed bottom bar carries it. */}
      <div className="max-lg:hidden">
        <SendButton label={button.label} busy={button.busy} disabled={button.disabled} onClick={onSubmit} className="h-[52px] px-8 text-[15.5px] font-semibold" />
      </div>
    </section>
  )
}

export default AnswerComposer
