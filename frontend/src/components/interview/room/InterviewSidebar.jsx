import { RoleBadgeIcon } from '../../ui/interviewIcons.jsx'
import InterviewRoadmap from './InterviewRoadmap.jsx'

// A quiet, supportive panel — not a dashboard. Role, the round, a compact
// progress line, the real interview plan (see InterviewRoadmap), and the
// guidance this room has always shown. Deliberately omits difficulty,
// question limit/position, format, scores, or any internal action/provider
// name: none of that is candidate-facing anywhere else in the product
// either. The interviewer + question stay the room's actual focal point —
// this column supports, it doesn't compete.
function InterviewSidebar({
  roleLabel,
  answeredCount = 0,
  topics = [],
  currentTopic,
  answeredTopics = [],
  className = '',
}) {
  return (
    <aside
      className={`flex flex-col gap-4 rounded-[var(--radius-panel)] border border-glass/70 bg-glass/50 p-4 lg:max-h-full lg:overflow-y-auto xl:p-5 ${className}`}
    >
      <div className="flex items-center gap-3">
        <RoleBadgeIcon className="h-6 w-6 shrink-0 text-primary" />
        <div className="min-w-0">
          <p className="text-base font-semibold leading-snug text-ink">{roleLabel ?? 'Technical Interview'}</p>
          <p className="text-sm text-muted">Technical Round</p>
        </div>
      </div>

      {answeredCount > 0 && (
        <p className="text-xs font-medium text-muted">
          {answeredCount} {answeredCount === 1 ? 'answer' : 'answers'} recorded so far
        </p>
      )}

      <InterviewRoadmap topics={topics} currentTopic={currentTopic} answeredTopics={answeredTopics} />

      <div className="mt-auto border-t border-line pt-4">
        <p className="text-xs font-semibold uppercase tracking-[0.15em] text-muted">Guidance</p>
        <p className="mt-2 text-sm leading-relaxed text-muted">
          Take your time and think out loud — the interviewer adapts to how you answer.
        </p>
      </div>
    </aside>
  )
}

export default InterviewSidebar
