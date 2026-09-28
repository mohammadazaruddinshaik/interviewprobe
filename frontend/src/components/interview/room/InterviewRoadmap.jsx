import { CompletionIcon, RoadmapIcon } from '../../ui/interviewIcons.jsx'
import { TOPIC_LABELS } from '../../../data/interviewCatalog.js'

// A quiet editorial progress rail, built from `topics` exactly as GET
// /interviews/{id} returns it — the candidate's own persisted topic
// selection (set at creation, in `sequence_number` order). Never the
// internal action the adaptive engine took (FOLLOW_UP/DEEP_DIVE/CHALLENGE/
// etc.) and never a fabricated bookend stage ("Welcome"/"Resume"/
// "Closing") — those aren't real signals this room has, so they're left
// out rather than invented. Labels route through the same TOPIC_LABELS
// map the Setup page already uses.
//
// Each topic's completed/current/pending state is deliberately NOT read
// from `entry.status`: that snapshot is only ever as fresh as the last
// full page load (POST /interviews/{id}/start, which really does move the
// first topic to IN_PROGRESS, has no response field that tells this room
// so — and the adaptive engine can choose ANY remaining topic for a
// NEW_TOPIC transition, not strictly the next sequence_number, so this
// room can't safely infer completion by position either). Instead this
// derives status from two things the room genuinely has live, at all
// times: `currentTopic` (the real topic of the question on screen right
// now) and `answeredTopics` (the real topics of every answer actually
// submitted this session) — both already correct with no extra request.
function InterviewRoadmap({ topics = [], currentTopic, answeredTopics = [] }) {
  if (topics.length === 0) return null

  const ordered = [...topics].sort((a, b) => a.sequence_number - b.sequence_number)
  const answered = new Set(answeredTopics)

  return (
    <div className="border-t border-line pt-4">
      <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-[0.15em] text-muted">
        <RoadmapIcon className="h-3.5 w-3.5" />
        Interview plan
      </p>

      <ol className="mt-3 flex flex-col">
        {ordered.map((entry, index) => {
          const isLast = index === ordered.length - 1
          const isCompleted = answered.has(entry.topic)
          const isCurrent = !isCompleted && entry.topic === currentTopic
          const label = TOPIC_LABELS[entry.topic] ?? entry.topic

          return (
            <li key={entry.topic} aria-current={isCurrent ? 'step' : undefined} className="relative flex gap-2.5 pb-3.5 last:pb-0">
              {!isLast && (
                <span
                  aria-hidden="true"
                  className={`absolute left-[5px] top-4 h-full w-px ${isCompleted ? 'bg-primary/30' : 'bg-line'}`}
                />
              )}
              <span aria-hidden="true" className="relative z-10 mt-0.5 flex h-3 w-3 shrink-0 items-center justify-center">
                {isCompleted ? (
                  <CompletionIcon className="h-3.5 w-3.5 -m-0.5 text-primary/70" />
                ) : (
                  <span
                    className={`h-2.5 w-2.5 rounded-full ${
                      isCurrent ? 'bg-primary ring-4 ring-primary/20' : 'bg-line'
                    }`}
                  />
                )}
              </span>
              <span
                className={`text-sm leading-snug ${
                  isCurrent ? 'font-semibold text-ink' : isCompleted ? 'text-muted' : 'text-muted/60'
                }`}
              >
                {label}
              </span>
            </li>
          )
        })}
      </ol>
    </div>
  )
}

export default InterviewRoadmap
