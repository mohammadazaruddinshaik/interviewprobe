import { BookIcon, ChartIcon, ChatIcon, UsersIcon } from '../ui/icons.jsx'

const FEATURES = [
  {
    icon: ChatIcon,
    title: 'Adaptive Questions',
    description: 'Questions respond to your answers.',
  },
  {
    icon: ChartIcon,
    title: 'Detailed Feedback',
    description: 'Understand exactly where your reasoning can improve.',
  },
  {
    icon: BookIcon,
    title: 'Multiple Roles',
    description: 'Practice AI, Backend, Frontend, Java and more.',
  },
  {
    icon: UsersIcon,
    title: 'Built for Students',
    description: 'Prepare before the pressure is real.',
  },
]

function FeatureStrip() {
  return (
    <section id="product" className="border-t border-line/70">
      <div className="mx-auto max-w-7xl px-6 py-16">
        <div className="grid grid-cols-1 gap-10 sm:grid-cols-2 lg:grid-cols-4 lg:gap-0">
          {FEATURES.map((feature, index) => (
            <div
              key={feature.title}
              className={`flex flex-col gap-3 ${
                index > 0 ? 'lg:border-l lg:border-line/70 lg:pl-8' : ''
              }`}
            >
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent-soft text-accent">
                <feature.icon className="h-5 w-5" />
              </span>
              <h3 className="text-base font-semibold text-ink">{feature.title}</h3>
              <p className="text-sm leading-relaxed text-muted">{feature.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

export default FeatureStrip
