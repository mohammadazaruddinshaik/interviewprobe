import { BookIcon, ChartIcon, ChatIcon, MicIcon, SparkIcon } from '../ui/icons.jsx'
import FeatureCard from './FeatureCard.jsx'

const FEATURES = [
  {
    icon: ChatIcon,
    title: 'AI-Powered Interviews',
    description: 'Adaptive, role-specific questions.',
  },
  {
    icon: MicIcon,
    title: 'Voice-First Experience',
    description: 'Natural, real-time conversation.',
  },
  {
    icon: ChartIcon,
    title: 'Detailed Feedback',
    description: 'Strengths, gaps, and suggestions.',
  },
  {
    icon: BookIcon,
    title: 'Multiple Roles',
    description: 'AI Engineer, Backend, Frontend +',
  },
  {
    icon: SparkIcon,
    title: 'Real Interview Simulation',
    description: 'Technical, adaptive, and structured.',
  },
]

function FeatureStrip() {
  return (
    <section id="features" className="scroll-mt-28 px-6 py-16">
      <div className="mx-auto grid max-w-7xl grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {FEATURES.map((feature) => (
          <FeatureCard key={feature.title} icon={feature.icon} title={feature.title} description={feature.description} />
        ))}
      </div>
    </section>
  )
}

export default FeatureStrip
