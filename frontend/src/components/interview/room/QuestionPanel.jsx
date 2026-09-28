import { QuestionIcon } from '../../ui/interviewIcons.jsx'

// The room's visual focus — the current question, and only the question.
// The candidate's spoken answer never appears here: it goes to the live
// caption strip and the transcript panel instead (see VoiceInterviewView),
// so this block stays visually stable turn after turn rather than growing
// underneath the question. `questionId` keys the transition wrapper so a
// genuinely new question gets a brief, restrained fade + settle
// (`question-in`, 0.35s) — the same element re-keying naturally replays it
// on every change, never a perpetual/looping effect.
function QuestionPanel({ questionText, questionId, leadIn, headingRef }) {
  return (
    <section className="flex shrink-0 flex-col gap-2.5 rounded-[var(--radius-panel)] border border-glass/60 bg-glass/40 px-5 py-5 sm:px-7 sm:py-6 lg:min-h-[9.5rem] lg:shrink">
      <div className="flex shrink-0 items-center gap-2 text-sm text-muted">
        <QuestionIcon className="h-4.5 w-4.5 text-primary" />
        <span className="font-medium">Current question</span>
      </div>

      <div key={questionId} className="motion-safe:animate-question-in lg:min-h-0 lg:overflow-y-auto">
        {/* The interviewer's short reaction to the previous answer — spoken
            in the same TTS turn as the question, shown secondary to it.
            Ordinary interviewer speech, never a "correction" banner or
            system notice. */}
        {leadIn && leadIn.trim() && <p className="mb-1.5 text-sm text-muted">{leadIn}</p>}
        {/* The actual question text, verbatim — never paraphrased here.
            Focus is moved here programmatically for screen readers when a
            new question arrives; it's tabIndex -1 (never a Tab stop), so
            it shows no focus ring. */}
        <h2
          ref={headingRef}
          tabIndex={-1}
          className="text-xl font-semibold leading-snug tracking-tight text-ink outline-none! sm:text-2xl lg:text-xl xl:text-[1.65rem] 2xl:text-[1.85rem]"
        >
          {questionText}
        </h2>
      </div>
    </section>
  )
}

export default QuestionPanel
