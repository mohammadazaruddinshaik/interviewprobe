import { BarChart3, FileText, MessageCircle, Mic } from 'lucide-react'

const FEATURES = [
  {
    icon: MessageCircle,
    tint: 'mint',
    title: 'Realistic Questions',
    description: 'Role-specific, industry-relevant questions',
  },
  {
    icon: BarChart3,
    tint: 'purple',
    title: 'Adaptive Follow-ups',
    description: 'Questions adapt based on your answers',
  },
  {
    icon: FileText,
    tint: 'peach',
    title: 'Detailed Feedback',
    description: 'Strengths, improvements and suggestions',
  },
  {
    icon: Mic,
    tint: 'pink',
    title: 'Voice-First Experience',
    description: 'Natural, real-time conversation with AI',
  },
]

const TINT_CLASSES = {
  mint: 'bg-tint-mint-light text-tint-mint',
  purple: 'bg-tint-purple-light text-tint-purple',
  peach: 'bg-tint-peach-light text-tint-peach',
  pink: 'bg-tint-pink-light text-tint-pink',
}

function SetupFeatureList() {
  return (
    <div className="mx-auto flex w-full max-w-[360px] flex-col gap-1 rounded-2xl border border-glass/70 bg-glass/60 p-3 shadow-glass-sm">
      {FEATURES.map((feature) => (
        <div key={feature.title} className="flex items-center gap-2.5 py-1.5">
          <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg ${TINT_CLASSES[feature.tint]}`}>
            <feature.icon className="h-3.5 w-3.5" strokeWidth={1.75} />
          </span>
          <span className="min-w-0">
            <span className="block truncate text-xs font-semibold text-ink">{feature.title}</span>
            <span className="block truncate text-[11px] leading-tight text-muted">{feature.description}</span>
          </span>
        </div>
      ))}
    </div>
  )
}

export default SetupFeatureList
