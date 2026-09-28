import { TranscriptIcon } from '../../ui/interviewIcons.jsx'

// Transcript-first candidate speech: while the candidate is speaking (or
// has spoken but not yet pressed Finish Answer), the recognized text
// appears here — never underneath the question. This is read-only,
// display-only content; nothing here is an <input>/<textarea>/
// contenteditable, and nothing here ever submits anything on its own.
// Once Finish Answer actually submits, `answer` resets to '' and this
// strip disappears (via `hidden`, so it stays a stable, always-queryable
// landmark rather than mounting/unmounting) — the finalized turn then
// lives once, in the transcript panel, never duplicated here.
function LiveTranscript({ answer, interimTranscript, isActive }) {
  const hasContent = Boolean(answer || interimTranscript)

  return (
    <div
      className={`shrink-0 items-start gap-2.5 rounded-[var(--radius-card)] border border-primary/20 bg-primary-light-2 px-4 py-3 ${
        hasContent ? 'flex' : 'hidden'
      }`}
    >
      <TranscriptIcon className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
      <div className="min-w-0 flex-1">
        <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-[0.08em] text-primary">
          <span aria-hidden="true" className={`h-1.5 w-1.5 rounded-full bg-primary ${isActive ? 'motion-safe:animate-pulse' : ''}`} />
          Live transcript
        </p>
        <p className="mt-1 text-sm leading-relaxed text-ink">
          <span className="font-medium text-muted">You </span>
          {/* The exact text a real Deepgram final transcript (or, before
              it, an in-progress interim) delivers — nothing paraphrased,
              nothing added. `aria-label` keeps its accessible name exactly
              the answer text itself, independent of the "You" chrome
              beside it. */}
          <span aria-label="Your answer" aria-live="polite">
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
          </span>
        </p>
      </div>
    </div>
  )
}

export default LiveTranscript
