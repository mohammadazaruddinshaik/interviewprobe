import { Calendar, Clock, Gauge, ListChecks } from 'lucide-react'
import Badge from '../ui/Badge.jsx'
import GlassCard from '../ui/GlassCard.jsx'
import { RoleBadgeIcon } from '../ui/interviewIcons.jsx'

function formatDate(isoString) {
  if (!isoString) return null
  return new Date(isoString).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

// Real elapsed time between the two persisted timestamps this session
// actually has — never a client-side timer, never estimated.
function formatDuration(startedAt, completedAt) {
  if (!startedAt || !completedAt) return null
  const minutes = Math.round((new Date(completedAt).getTime() - new Date(startedAt).getTime()) / 60000)
  if (minutes < 1) return 'Under a minute'
  if (minutes < 60) return `${minutes} minute${minutes === 1 ? '' : 's'}`
  const hours = Math.floor(minutes / 60)
  const remainder = minutes % 60
  return `${hours}h ${remainder}m`
}

// A compact, single-glance summary of the session itself — nothing here
// is inferred or invented: every stat traces directly to a field
// `GET /interviews/{id}/result` actually returns. Candidate-facing only —
// no internal orchestration state (topics/actions/providers) appears.
function InterviewSummary({ roleLabel, difficultyLabel, startedAt, completedAt, questionCount, className = '' }) {
  const date = formatDate(completedAt)
  const duration = formatDuration(startedAt, completedAt)

  const stats = [
    date && { icon: Calendar, label: date },
    duration && { icon: Clock, label: duration },
    questionCount != null && { icon: ListChecks, label: `${questionCount} question${questionCount === 1 ? '' : 's'}` },
    difficultyLabel && { icon: Gauge, label: difficultyLabel },
  ].filter(Boolean)

  return (
    <GlassCard className={`flex flex-col gap-4 p-5 sm:p-6 ${className}`}>
      <div className="flex items-center gap-3">
        <RoleBadgeIcon className="h-6 w-6 shrink-0 text-primary" />
        <div className="flex min-w-0 flex-wrap items-center gap-2.5">
          <p className="text-lg font-semibold leading-snug text-ink">{roleLabel}</p>
          <Badge tone="primary">Technical Round</Badge>
        </div>
      </div>

      {stats.length > 0 && (
        <div className="flex flex-wrap gap-x-6 gap-y-2.5 border-t border-line pt-4">
          {stats.map(({ icon: Icon, label }) => (
            <span key={label} className="flex items-center gap-2 text-sm text-muted">
              <Icon className="h-4 w-4 text-ink/50" strokeWidth={1.75} aria-hidden="true" />
              <span className="font-medium text-ink">{label}</span>
            </span>
          ))}
        </div>
      )}
    </GlassCard>
  )
}

export default InterviewSummary
