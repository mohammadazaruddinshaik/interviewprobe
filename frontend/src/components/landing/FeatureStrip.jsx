import { AdaptiveIcon, EvaluationIcon, NeuralChipIcon, VoiceInterviewIcon } from '../ui/interviewIcons.jsx'

const FEATURES = [
  { icon: NeuralChipIcon, title: 'AI-Powered', description: 'Role-aware interviews' },
  { icon: VoiceInterviewIcon, title: 'Voice-First', description: 'Natural conversation' },
  { icon: AdaptiveIcon, title: 'Adaptive', description: 'Questions follow your answers' },
  { icon: EvaluationIcon, title: 'Feedback', description: 'Clear strengths and gaps' },
]

// A refined horizontal capability rail — not a row of cards. Four short
// entries, each just an icon and a couple of words, so it reads at a
// glance rather than asking to be read paragraph by paragraph.
function FeatureStrip() {
  return (
    <section id="features" className="scroll-mt-4 border-y border-line/70 px-4 py-5 sm:px-6 lg:px-10">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 lg:divide-x lg:divide-line/70">
        {FEATURES.map((feature, index) => (
          <div key={feature.title} className={`flex items-center gap-3 ${index > 0 ? 'lg:pl-6' : ''}`}>
            <feature.icon className="h-5 w-5 shrink-0 text-primary" strokeWidth={1.75} />
            <div>
              <h3 className="text-sm font-semibold leading-tight text-ink">{feature.title}</h3>
              <p className="mt-0.5 text-xs leading-snug text-muted">{feature.description}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

export default FeatureStrip
