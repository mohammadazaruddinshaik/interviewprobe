import GlassCard from '../ui/GlassCard.jsx'
import { CheckIcon, TargetIcon } from '../ui/icons.jsx'
import { EvaluationIcon } from '../ui/interviewIcons.jsx'

// One column of the feedback — a plain editorial list under a small
// colored marker, not a tinted card. Color is used only for the marker
// and each item's glyph, so the section reads as one piece of writing.
function FeedbackColumn({ title, items, icon: Icon, tone, emptyMessage, className = '' }) {
  return (
    <div className={`flex min-w-0 flex-col gap-3 ${className}`}>
      <h3 className="flex items-center gap-2 text-sm font-semibold text-ink">
        <span aria-hidden="true" className={`h-2 w-2 rounded-full ${tone.dot}`} />
        {title}
      </h3>
      {items.length === 0 ? (
        <p className="text-sm text-muted">{emptyMessage}</p>
      ) : (
        <ul className="flex flex-col gap-2.5">
          {items.map((item, index) => (
            <li key={index} className="flex items-start gap-2.5">
              <Icon className={`mt-1 h-3.5 w-3.5 shrink-0 ${tone.icon}`} />
              <p className="text-sm leading-relaxed text-ink">{item}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

// Real evaluation data only — `strengths`/`weaknesses` exactly as
// `GET /interviews/{id}/result` returns them. The reference also shows a
// third "Recommendations" column, but the evaluation schema has no such
// field; inventing one would mean showing feedback the model never gave,
// so this section stays at the two columns the API actually supports.
function FeedbackSection({ strengths, weaknesses, className = '' }) {
  return (
    <GlassCard className={`flex flex-col gap-5 p-5 sm:p-6 ${className}`}>
      <div className="flex items-center gap-3">
        <EvaluationIcon className="h-5 w-5 shrink-0 text-primary" />
        <div>
          <h2 className="text-base font-semibold text-ink">Detailed Feedback</h2>
          <p className="text-sm text-muted">Key strengths and areas for improvement</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 sm:gap-0 sm:divide-x sm:divide-line">
        <FeedbackColumn
          title="Strengths"
          items={strengths}
          icon={CheckIcon}
          tone={{ dot: 'bg-success', icon: 'text-success' }}
          className="sm:pr-6"
          emptyMessage="No specific strengths were identified for this interview."
        />
        <FeedbackColumn
          title="Areas for Improvement"
          items={weaknesses}
          icon={TargetIcon}
          tone={{ dot: 'bg-tint-peach', icon: 'text-tint-peach' }}
          className="sm:pl-6"
          emptyMessage="No specific areas for improvement were identified."
        />
      </div>
    </GlassCard>
  )
}

export default FeedbackSection
