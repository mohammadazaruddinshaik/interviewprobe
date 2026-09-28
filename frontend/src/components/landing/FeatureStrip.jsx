import {
  EvaluationIcon,
  InterviewerIcon,
  RolesIcon,
  SimulationIcon,
  VoiceInterviewIcon,
} from '../ui/interviewIcons.jsx'

// Only claims the product actually delivers today: an adaptive AI
// interviewer, spoken answers, a scored evaluation with evidence, seven
// real roles, and a video-call style room. Icons are small accents in one
// color, placed directly — the strip supports the hero, it doesn't
// compete with it.
const CAPABILITIES = [
  {
    icon: InterviewerIcon,
    title: 'AI-Powered Interviews',
    description: 'Role-specific, adaptive questions',
  },
  {
    icon: VoiceInterviewIcon,
    title: 'Voice-First Experience',
    description: 'Natural, spoken conversation',
  },
  {
    icon: EvaluationIcon,
    title: 'Detailed Feedback',
    description: 'Strengths, gaps and evidence',
  },
  {
    icon: RolesIcon,
    title: 'Multiple Roles',
    description: 'SDE, AI Engineer, Backend and more',
  },
  {
    icon: SimulationIcon,
    title: 'Real Interview Simulation',
    description: 'A live, video-call style room',
  },
]

// One glass band, divided rather than split into five separate cards.
function FeatureStrip() {
  return (
    <section id="features" className="scroll-mt-28 px-4 sm:px-6 lg:px-10">
      <div className="mx-auto max-w-[1280px] rounded-[var(--radius-panel)] border border-glass/70 bg-glass/45 px-5 py-4 backdrop-blur-xl sm:px-6">
        <ul className="grid grid-cols-1 gap-x-6 gap-y-5 sm:grid-cols-2 lg:grid-cols-5 lg:gap-0 lg:divide-x lg:divide-line">
          {CAPABILITIES.map(({ icon: Icon, title, description }) => (
            <li key={title} className="flex min-w-0 items-center gap-3 lg:px-4 lg:first:pl-0 lg:last:pr-0">
              <Icon className="h-5 w-5 shrink-0 text-primary" />
              <div className="min-w-0">
                <h3 className="text-sm font-semibold leading-snug text-ink">{title}</h3>
                <p className="mt-0.5 text-[13px] leading-snug text-muted">{description}</p>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}

export default FeatureStrip
