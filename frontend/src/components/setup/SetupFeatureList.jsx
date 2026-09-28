import { AdaptiveIcon, EvaluationIcon, QuestionIcon, VoiceInterviewIcon } from '../ui/interviewIcons.jsx'

// What the candidate is about to get, in the product's own icon family
// (never generic Lucide concept icons), placed directly as accents.
// Every line describes real behavior: role-specific questions, adaptive
// follow-ups, a scored evaluation with strengths and gaps, and spoken
// answers.
const FEATURES = [
  {
    icon: QuestionIcon,
    title: 'Realistic Questions',
    description: 'Role-specific, industry-relevant questions',
  },
  {
    icon: AdaptiveIcon,
    title: 'Adaptive Follow-ups',
    description: 'Questions adapt based on your answers',
  },
  {
    icon: EvaluationIcon,
    title: 'Detailed Feedback',
    description: 'Strengths, gaps and evidence',
  },
  {
    icon: VoiceInterviewIcon,
    title: 'Voice-First Experience',
    description: 'Natural, spoken conversation with AI',
  },
]

// On short desktop viewports this secondary list (it restates the
// Landing page's claims) steps aside so the page itself never scrolls;
// the role list, preview and Start Interview always stay.
function SetupFeatureList() {
  return (
    <ul className="mx-auto flex w-full max-w-[360px] xl:max-w-none flex-col gap-0.5 rounded-[var(--radius-card)] border border-glass/70 bg-glass/60 px-3 py-2 shadow-glass-sm lg:[@media(max-height:790px)]:hidden">
      {FEATURES.map(({ icon: Icon, title, description }) => (
        <li key={title} className="flex items-center gap-3 py-1 2xl:py-2">
          <Icon className="h-4.5 w-4.5 shrink-0 text-primary 2xl:h-5 2xl:w-5" />
          <span className="min-w-0">
            <span className="block truncate text-xs font-semibold text-ink 2xl:text-sm">{title}</span>
            <span className="block truncate text-[11px] leading-tight text-muted 2xl:text-xs">{description}</span>
          </span>
        </li>
      ))}
    </ul>
  )
}

export default SetupFeatureList
