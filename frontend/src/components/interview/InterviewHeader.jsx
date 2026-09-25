import { BrandMark } from '../ui/icons.jsx'

// A professional Technical Round should read like an interview, not a
// configuration summary — this header shows only the brand and the role
// being interviewed for. It deliberately does not surface internal
// mechanics (question number/limit, topic, difficulty, action names): those
// remain real backend/session data (see Interview.jsx's sessionMeta and the
// question object), just no longer part of the candidate-facing header.
function InterviewHeader({ roleLabel }) {
  return (
    <header className="border-b border-line/70">
      <div className="mx-auto flex max-w-3xl items-center justify-between gap-6 px-6 py-5 sm:px-8">
        <div className="flex items-center gap-1.5 text-ink">
          <BrandMark className="h-4 w-4 text-accent" />
          <span className="text-sm font-semibold tracking-tight">InterviewProbe</span>
        </div>

        <div className="text-right">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent">Technical Round</p>
          {roleLabel && <p className="mt-1 text-sm font-medium text-ink">{roleLabel}</p>}
        </div>
      </div>
    </header>
  )
}

export default InterviewHeader
