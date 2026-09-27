import { AdaptiveIcon, EvaluationIcon, RoleBadgeIcon } from '../ui/interviewIcons.jsx'

const ITEMS = [
  {
    icon: RoleBadgeIcon,
    title: 'Role-Specific Interviews',
    description: 'Tailored question sets for the role being practiced.',
  },
  {
    icon: AdaptiveIcon,
    title: 'Adaptive Questioning',
    description: "The interviewer responds to the candidate's actual answer and chooses the next direction.",
  },
  {
    icon: EvaluationIcon,
    title: 'Detailed Evaluation',
    description: 'Structured feedback on technical knowledge, reasoning, depth and communication.',
  },
]

// An editorial two-column composition, not a row of three identical
// cards: a fixed heading column on the left, and a divided, borderless
// list on the right — typography and a thin rule doing the work that a
// pastel card + shadow used to.
function FeatureCardGrid() {
  return (
    <section id="capabilities" className="scroll-mt-4 px-4 py-10 sm:px-6 lg:px-10 lg:py-14">
      <div className="mx-auto grid max-w-5xl gap-8 lg:grid-cols-[240px_1fr] lg:gap-16">
        <div>
          <h2 className="text-2xl font-bold leading-snug tracking-tight text-ink sm:text-[1.75rem]">
            Why InterviewProbe
          </h2>
        </div>

        <div className="flex flex-col divide-y divide-line">
          {ITEMS.map((item) => (
            <div key={item.title} className="flex items-start gap-5 py-6 first:pt-0 last:pb-0">
              <span className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-line text-primary">
                <item.icon className="h-4.5 w-4.5" strokeWidth={1.75} />
              </span>
              <div>
                <h3 className="text-base font-semibold text-ink">{item.title}</h3>
                <p className="mt-1 max-w-md text-sm leading-relaxed text-muted">{item.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

export default FeatureCardGrid
