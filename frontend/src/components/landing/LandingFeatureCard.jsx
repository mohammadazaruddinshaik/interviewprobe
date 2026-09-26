import { ArrowRight } from 'lucide-react'

// The four pastel tints the reference's lower card grid cycles through —
// an outer neutral glass shell always wraps an inner tinted panel, per
// tint, so every LandingFeatureCard shares one recipe regardless of color.
const TINTS = {
  blue: {
    panel: 'from-primary-light/70 to-white/40',
    icon: 'bg-white/80 text-primary',
    arrow: 'bg-white/80 text-primary hover:bg-white',
  },
  purple: {
    panel: 'from-tint-purple-light/70 to-white/40',
    icon: 'bg-white/80 text-tint-purple',
    arrow: 'bg-white/80 text-tint-purple hover:bg-white',
  },
  mint: {
    panel: 'from-tint-mint-light/70 to-white/40',
    icon: 'bg-white/80 text-tint-mint',
    arrow: 'bg-white/80 text-tint-mint hover:bg-white',
  },
  peach: {
    panel: 'from-tint-peach-light/70 to-white/40',
    icon: 'bg-white/80 text-tint-peach',
    arrow: 'bg-white/80 text-tint-peach hover:bg-white',
  },
}

function LandingFeatureCard({ icon: Icon, title, description, tint = 'blue' }) {
  const colors = TINTS[tint] ?? TINTS.blue

  return (
    <div className="group rounded-[26px] border border-white/70 bg-white/50 p-1 shadow-glass-sm transition-transform duration-200 hover:-translate-y-1">
      <div className={`flex h-full flex-col rounded-[20px] bg-gradient-to-br p-5 ${colors.panel}`}>
        <span className={`flex h-10 w-10 items-center justify-center rounded-xl border border-white/70 ${colors.icon}`}>
          <Icon className="h-5 w-5" strokeWidth={1.75} />
        </span>
        <h3 className="mt-3.5 text-base font-semibold text-ink">{title}</h3>
        <p className="mt-1.5 text-sm leading-snug text-muted">{description}</p>
        <button
          type="button"
          aria-label={`Learn more about ${title}`}
          className={`mt-4 flex h-8 w-8 items-center justify-center self-end rounded-full transition-colors duration-200 ${colors.arrow}`}
        >
          <ArrowRight className="h-4 w-4 transition-transform duration-200 group-hover:translate-x-0.5" strokeWidth={1.75} />
        </button>
      </div>
    </div>
  )
}

export default LandingFeatureCard
