import { useEffect, useRef, useState } from 'react'

// Matches the backend's answer length cap (SubmitAnswerRequest.answer).
const MAX_ANSWER_LENGTH = 10_000

// The room's other visual focal point (after the interviewer) — the
// current question, verbatim, in large type, with the candidate's own
// editable answer directly beneath it. Never shows difficulty, topic,
// question number/limit, or any internal action name: only what this
// product has ever shown the candidate.
function QuestionPanel({ questionText, leadIn, interimTranscript, answer, onAnswerChange, onSubmit, submitting, headingRef }) {
  // Purely cosmetic "previous line fades" continuity — not voice state, so
  // it's tracked locally rather than added to the session.
  const previousQuestionRef = useRef(null)
  const [previousQuestionText, setPreviousQuestionText] = useState(null)

  useEffect(() => {
    if (previousQuestionRef.current !== null && previousQuestionRef.current !== questionText) {
      setPreviousQuestionText(previousQuestionRef.current)
    }
    previousQuestionRef.current = questionText
  }, [questionText])

  const canSubmit = answer.trim().length > 0 && !submitting

  function handleKeyDown(event) {
    if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
      event.preventDefault()
      if (canSubmit) onSubmit()
    }
  }

  return (
    <section className="motion-safe:animate-rise flex flex-col gap-4 rounded-[22px] border border-glass/70 bg-glass/60 p-5 shadow-glass-sm sm:p-6">
      <div>
        {previousQuestionText && <p className="truncate text-xs text-muted/70">{previousQuestionText}</p>}
        {/* The interviewer's short conversational reaction to the previous
            answer — spoken as part of the same TTS turn as the question,
            shown visually secondary to it: smaller, lighter, above the
            actual question heading rather than merged into it. */}
        {leadIn && leadIn.trim() && <p className="text-sm text-muted">{leadIn}</p>}
        {/* The actual question text, verbatim — never paraphrased here. */}
        <h2
          ref={headingRef}
          tabIndex={-1}
          className="mt-1 rounded-lg text-xl font-semibold leading-snug text-ink focus:outline focus:outline-2 focus:outline-primary focus:outline-offset-4 sm:text-2xl"
        >
          {questionText}
        </h2>
      </div>

      <div className="border-t border-line pt-4">
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs font-semibold uppercase tracking-[0.15em] text-muted">Your answer</p>
          <span className="text-xs text-muted">
            {answer.length.toLocaleString()} / {MAX_ANSWER_LENGTH.toLocaleString()}
          </span>
        </div>

        {interimTranscript && (
          <p className="mt-1.5 text-sm italic text-muted" aria-live="polite">
            {interimTranscript}
            <span aria-hidden="true" className="motion-safe:animate-pulse">
              …
            </span>
          </p>
        )}

        <textarea
          value={answer}
          onChange={(event) => onAnswerChange(event.target.value)}
          onKeyDown={handleKeyDown}
          disabled={submitting}
          placeholder="Your answer will appear here as you speak — or type it directly."
          rows={4}
          maxLength={MAX_ANSWER_LENGTH}
          aria-label="Your answer"
          className="mt-2 w-full resize-y rounded-xl border border-line bg-glass/70 p-3 text-sm leading-relaxed text-ink placeholder:text-ink/35 transition-colors duration-200 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 disabled:cursor-not-allowed disabled:opacity-60"
        />
      </div>
    </section>
  )
}

export default QuestionPanel
