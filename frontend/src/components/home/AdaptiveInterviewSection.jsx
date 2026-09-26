import GlassCard from '../ui/GlassCard.jsx'
import SectionHeading from '../ui/SectionHeading.jsx'
import { ChatIcon, CodeIcon, SparkIcon, TargetIcon } from '../ui/icons.jsx'

// Describes the real backend decision engine (LangGraph choosing between
// probing deeper, clarifying, challenging, or moving on — see
// backend/app/workflows/interview/nodes.py) in plain, candidate-facing
// language, never the internal action names the API itself never exposes.
const OUTCOMES = [
  {
    icon: TargetIcon,
    title: 'Probes deeper',
    description: 'Pushes further into a concept you clearly understand.',
  },
  {
    icon: ChatIcon,
    title: 'Asks for clarity',
    description: 'Follows up when an answer is vague or incomplete.',
  },
  {
    icon: CodeIcon,
    title: 'Pressure-tests your design',
    description: 'Introduces a constraint or edge case to your approach.',
  },
  {
    icon: SparkIcon,
    title: 'Moves the interview on',
    description: 'Switches topics once yours is genuinely covered.',
  },
]

function AdaptiveInterviewSection() {
  return (
    <section id="how-it-works" className="scroll-mt-28 px-6 py-20">
      <div className="mx-auto grid max-w-7xl gap-14 lg:grid-cols-2 lg:items-center lg:gap-16">
        <SectionHeading
          eyebrow="Adaptive by Design"
          title="Every question depends on what you just said."
          description="There's no fixed script. After each answer, the interviewer weighs what you demonstrated, what you left unclear, and how much of the topic is left — then decides what a real interviewer would ask next."
        />

        <GlassCard className="grid grid-cols-1 gap-3 p-4 sm:grid-cols-2 sm:p-5">
          {OUTCOMES.map((outcome) => (
            <div key={outcome.title} className="flex flex-col gap-2.5 rounded-2xl bg-white/70 p-4">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary-light text-primary">
                <outcome.icon className="h-4.5 w-4.5" />
              </span>
              <h3 className="text-sm font-semibold text-ink">{outcome.title}</h3>
              <p className="text-xs leading-relaxed text-muted">{outcome.description}</p>
            </div>
          ))}
        </GlassCard>
      </div>
    </section>
  )
}

export default AdaptiveInterviewSection
