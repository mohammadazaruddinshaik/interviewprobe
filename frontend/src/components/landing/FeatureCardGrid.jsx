import { Brain, GraduationCap, LineChart, MessageCircle } from 'lucide-react'
import LandingFeatureCard from './LandingFeatureCard.jsx'

const CARDS = [
  {
    icon: Brain,
    tint: 'blue',
    title: 'Role-Specific Interviews',
    description: 'Practice for AI Engineer, SDE, Backend, Frontend and more with tailored question sets.',
  },
  {
    icon: MessageCircle,
    tint: 'purple',
    title: 'Adaptive Questioning',
    description: 'The interviewer adapts based on your answers — follow-ups, deeper questions, or new topics.',
  },
  {
    icon: LineChart,
    tint: 'mint',
    title: 'Detailed Evaluation',
    description: 'Get structured feedback on technical knowledge, reasoning, depth and communication.',
  },
  {
    icon: GraduationCap,
    tint: 'peach',
    title: 'Learn and Improve',
    description: 'Use feedback, transcripts and resources to strengthen your concepts and track progress.',
  },
]

function FeatureCardGrid() {
  return (
    <section id="capabilities" className="scroll-mt-4 px-4 pb-6 pt-2 sm:px-6 lg:px-10 lg:pb-8">
      <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2 lg:grid-cols-4">
        {CARDS.map((card) => (
          <LandingFeatureCard
            key={card.title}
            icon={card.icon}
            tint={card.tint}
            title={card.title}
            description={card.description}
          />
        ))}
      </div>
    </section>
  )
}

export default FeatureCardGrid
