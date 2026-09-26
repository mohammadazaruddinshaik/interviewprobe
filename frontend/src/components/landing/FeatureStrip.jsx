import { BarChart3, BookOpen, MessageCircle, Mic, Zap } from 'lucide-react'

const FEATURES = [
  {
    icon: MessageCircle,
    title: 'AI-Powered Interviews',
    description: 'Adaptive, role-specific questions',
  },
  {
    icon: Mic,
    title: 'Voice-First Experience',
    description: 'Natural, real-time conversation',
  },
  {
    icon: BarChart3,
    title: 'Detailed Feedback',
    description: 'Strengths, gaps and suggestions',
  },
  {
    icon: BookOpen,
    title: 'Multiple Roles',
    description: 'SDE, AI Engineer, Backend, Frontend +',
  },
  {
    icon: Zap,
    title: 'Real Interview Simulation',
    description: 'Technical, behavioral and more',
  },
]

function FeatureStrip() {
  return (
    <section id="features" className="scroll-mt-4 border-y border-line/70 px-4 py-5 sm:px-6 lg:px-10">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5 lg:divide-x lg:divide-line/70">
        {FEATURES.map((feature, index) => (
          <div key={feature.title} className={`flex items-start gap-2.5 ${index > 0 ? 'lg:pl-5' : ''}`}>
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-white/70 bg-primary-light text-primary">
              <feature.icon className="h-4 w-4" strokeWidth={2} />
            </span>
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
