import { AdaptiveIcon, EvaluationIcon, RoleBadgeIcon } from '../ui/interviewIcons.jsx'

// The three product decisions that make InterviewProbe what it is, each
// described exactly as the product behaves: questions drawn from the
// selected role, follow-ups driven by the actual answer, and a scored
// evaluation across the four real dimensions.
const DECISIONS = [
  {
    icon: RoleBadgeIcon,
    title: 'Role-Specific Interviews',
    description: 'Questions tailored to the role you choose, from SDE Intern to AI Engineer.',
  },
  {
    icon: AdaptiveIcon,
    title: 'Adaptive Questioning',
    description: 'Follow-ups, deeper probes or a new topic, based on what you actually said.',
  },
  {
    icon: EvaluationIcon,
    title: 'Detailed Evaluation',
    description: 'Scores for technical knowledge, reasoning, depth and communication, with evidence.',
  },
]

// A short manifesto, not a card grid: an eyebrow, one statement, then
// three principles set in columns and separated by thin rules. No card
// surfaces, shadows, or icon containers — typography carries it.
function WhySection() {
  return (
    <section id="why" className="scroll-mt-28 px-4 pb-14 pt-16 sm:px-6 lg:px-10 lg:pb-20 lg:pt-20">
      <div className="mx-auto max-w-[1280px]">
        <div className="mx-auto max-w-4xl text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">Why InterviewProbe</p>
          <h2 className="mt-3 text-3xl font-bold leading-tight tracking-tight text-ink sm:text-4xl">
            Everything you need to{' '}
            <span className="bg-gradient-to-r from-primary to-accent-2 bg-clip-text text-transparent">
              interview with confidence
            </span>
          </h2>
        </div>

        <ul className="mt-12 grid grid-cols-1 divide-y divide-line border-y border-line lg:grid-cols-3 lg:divide-x lg:divide-y-0">
          {DECISIONS.map(({ icon: Icon, title, description }) => (
            <li key={title} className="py-7 lg:px-8 lg:py-8 lg:first:pl-2 lg:last:pr-2">
              <Icon className="h-6 w-6 text-primary" />
              <h3 className="mt-4 text-lg font-semibold text-ink">{title}</h3>
              <p className="mt-2 max-w-sm text-[15px] leading-relaxed text-muted">{description}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}

export default WhySection
