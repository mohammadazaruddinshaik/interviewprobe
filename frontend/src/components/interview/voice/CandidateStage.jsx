import ListeningIndicator from './ListeningIndicator.jsx'

// Deliberately smaller and quieter than InterviewerStage — presence only,
// audio-only (no webcam), never competing for visual weight.
function CandidateStage({ status }) {
  return (
    <aside className="flex flex-row items-center gap-3 rounded-2xl border border-line bg-white/60 p-4 lg:flex-col lg:items-center lg:justify-center lg:gap-2 lg:p-6 lg:text-center">
      <div
        aria-hidden="true"
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-line bg-cream-soft text-xs font-semibold text-ink lg:h-14 lg:w-14 lg:text-sm"
      >
        You
      </div>
      <div className="min-w-0">
        <p className="text-sm font-medium text-ink lg:mt-1">You</p>
        <ListeningIndicator status={status} />
      </div>
    </aside>
  )
}

export default CandidateStage
