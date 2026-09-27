import { NeuralChipIcon } from '../../ui/interviewIcons.jsx'

// One cohesive surface, not a stack of dashboard cards — the candidate's
// selected role (the only session detail this room shows) plus a short,
// static piece of guidance. Deliberately omits difficulty, topic,
// question count/limit, and any internal action name: none of that is
// candidate-facing anywhere else in the product either.
function InterviewSidebar({ roleLabel, className = '' }) {
  return (
    <aside
      className={`flex flex-col gap-4 rounded-[22px] border border-glass/70 bg-glass/60 p-4 shadow-glass-sm lg:p-5 ${className}`}
    >
      <div className="flex items-center gap-3">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary-light text-primary">
          <NeuralChipIcon className="h-5 w-5" />
        </span>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-ink">{roleLabel ?? 'Technical Interview'}</p>
          <p className="text-xs font-semibold uppercase tracking-[0.15em] text-muted">Technical Round</p>
        </div>
      </div>

      <div className="border-t border-line pt-4">
        <p className="text-xs font-semibold uppercase tracking-[0.15em] text-muted">Guidance</p>
        <p className="mt-2 text-sm leading-relaxed text-muted">
          Take your time and think out loud — the interviewer adapts to how you answer.
        </p>
      </div>
    </aside>
  )
}

export default InterviewSidebar
