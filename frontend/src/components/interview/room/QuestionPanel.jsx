import { Mic } from 'lucide-react'
import { QuestionIcon } from '../../ui/interviewIcons.jsx'

// The current question, verbatim and prominent, attached directly under
// the interviewer — part of the room, not a form. Never shows difficulty,
// topic, question number/limit, or any internal action name.
//
// This room is voice-first with no typed-answer escape hatch: there is no
// text input here, and the candidate never edits what Deepgram
// transcribed. `answer` (the finalized transcript captured so far) and
// `interimTranscript` (the in-progress utterance) are rendered as plain,
// read-only live captions — the same idea as a video call's captions —
// so the candidate can see what was heard without being able to change
// it. Finish Answer, not this text, is what the candidate actually
// controls; submitting still reads this same `answer` value exactly as
// before.
function QuestionPanel({ questionText, leadIn, interimTranscript, answer, headingRef }) {
  const hasCaption = Boolean(answer || interimTranscript)

  return (
    <section className="motion-safe:animate-rise flex shrink-0 flex-col gap-2 rounded-[var(--radius-panel)] border border-glass/60 bg-glass/40 px-5 py-4 sm:px-6 lg:min-h-[8.5rem] lg:shrink">
      <div className="flex shrink-0 items-center gap-2 text-sm text-muted">
        <QuestionIcon className="h-4.5 w-4.5 text-primary" />
        <span className="font-medium">Current question</span>
      </div>

      {/* On a short desktop viewport with an unusually long question, only
          this text scrolls (inside the block) — the room never overflows. */}
      <div className="lg:min-h-0 lg:overflow-y-auto">
        {/* The interviewer's short reaction to the previous answer — spoken
            in the same TTS turn as the question, shown secondary to it. */}
        {leadIn && leadIn.trim() && <p className="mb-1 text-sm text-muted">{leadIn}</p>}
        {/* The actual question text, verbatim — never paraphrased here.
            Focus is moved here programmatically for screen readers when a
            new question arrives; it's tabIndex -1 (never a Tab stop), so
            it shows no focus ring. */}
        <h2
          ref={headingRef}
          tabIndex={-1}
          className="text-lg font-semibold leading-snug tracking-tight text-ink outline-none! sm:text-xl lg:text-lg xl:text-[1.35rem] 2xl:text-[1.45rem]"
        >
          {questionText}
        </h2>
      </div>

      {/* Live, read-only captions — never an <input>/<textarea>, never
          focusable, never editable. The labelled element's own text is
          always exactly `answer` (+ any in-progress interim words),
          nothing else — mirroring the real, unmodified `answer` state
          Finish Answer will submit, so it reads as empty when there is
          nothing yet rather than showing placeholder copy as "content". */}
      <div
        className={`shrink-0 rounded-xl px-3 py-2 text-sm leading-relaxed transition-colors duration-200 ${
          hasCaption ? 'border border-primary/25 bg-primary-light-2' : 'border border-transparent'
        }`}
      >
        {!hasCaption && (
          <span aria-hidden="true" className="flex items-center gap-1.5 text-muted/70">
            <Mic className="h-3.5 w-3.5" strokeWidth={1.75} />
            Your spoken answer will appear here.
          </span>
        )}
        <p aria-label="Your answer" aria-live="polite" className={hasCaption ? 'text-ink' : 'sr-only'}>
          {answer}
          {interimTranscript && (
            <>
              {answer ? ' ' : ''}
              <span className="italic text-muted">{interimTranscript}</span>
              <span aria-hidden="true" className="motion-safe:animate-pulse">
                …
              </span>
            </>
          )}
        </p>
      </div>
    </section>
  )
}

export default QuestionPanel
