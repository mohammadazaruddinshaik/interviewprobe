import { useEffect, useRef, useState } from 'react'
import { VOICE_STATUS } from '../../../voice/voiceState.js'

// Matches the backend's answer length cap (SubmitAnswerRequest.answer).
const MAX_ANSWER_LENGTH = 10_000

const CANDIDATE_ACTIVE_STATUSES = [VOICE_STATUS.CANDIDATE_LISTENING, VOICE_STATUS.CANDIDATE_SPEAKING]

// The shared "who said what" rail for both speakers. The candidate's line
// is the same `answer` value/setter the text interview already uses —
// there is no second answer-storage mechanism here, just an editable
// presentation of the one that already exists.
function InterviewSubtitles({
  interviewerName,
  questionText,
  isInterviewerActive,
  status,
  interimTranscript,
  answer,
  onAnswerChange,
  onSubmit,
  submitting,
  headingRef,
}) {
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

  const isCandidateActive = CANDIDATE_ACTIVE_STATUSES.includes(status)
  const canSubmit = answer.trim().length > 0 && !submitting

  function handleKeyDown(event) {
    if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
      event.preventDefault()
      if (canSubmit) onSubmit()
    }
  }

  return (
    <div className="mt-6 space-y-4 rounded-2xl border border-line bg-white/60 p-5 text-left sm:p-6">
      {previousQuestionText && <p className="truncate text-xs text-muted/70">{previousQuestionText}</p>}

      <div>
        <p
          className={`text-xs font-semibold uppercase tracking-[0.2em] ${isInterviewerActive ? 'text-accent' : 'text-muted'}`}
        >
          {interviewerName}
        </p>
        {/* The actual question text, verbatim — never paraphrased here. */}
        <h2
          ref={headingRef}
          tabIndex={-1}
          className="mt-1 rounded-lg text-lg font-semibold leading-snug text-ink focus:outline focus:outline-2 focus:outline-accent focus:outline-offset-4 sm:text-xl"
        >
          {questionText}
        </h2>
      </div>

      <div className="border-t border-line pt-4">
        <div className="flex items-center justify-between gap-3">
          <p className={`text-xs font-semibold uppercase tracking-[0.2em] ${isCandidateActive ? 'text-accent' : 'text-muted'}`}>
            You
          </p>
          <span className="text-xs text-muted">
            {answer.length.toLocaleString()} / {MAX_ANSWER_LENGTH.toLocaleString()}
          </span>
        </div>

        {interimTranscript && (
          <p className="mt-1 text-sm italic text-muted" aria-live="polite">
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
          className="mt-2 w-full resize-y rounded-xl border border-line bg-white/70 p-3 text-sm leading-relaxed text-ink placeholder:text-ink/35 transition-colors duration-200 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20 disabled:cursor-not-allowed disabled:opacity-60"
        />
      </div>
    </div>
  )
}

export default InterviewSubtitles
