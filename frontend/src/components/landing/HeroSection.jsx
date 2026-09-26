import { Check, Play, Sparkles } from 'lucide-react'
import Badge from '../ui/Badge.jsx'
import Button from '../ui/Button.jsx'
import InterviewPreview from './InterviewPreview.jsx'

// Real product signals, standing in for the reference's fabricated
// "1,000+ students / 4.9 rating" social-proof row — every claim here is
// something the product actually does, not an unverifiable number.
const CAPABILITY_POINTS = ['Voice-first interviews', 'Role-specific questions', 'Structured evaluation']

function HeroSection() {
  return (
    <section id="top" className="scroll-mt-4 px-4 pb-6 pt-5 sm:px-6 sm:pb-8 sm:pt-6 lg:px-10 lg:pb-8 lg:pt-6">
      <div className="grid items-center gap-8 lg:grid-cols-[43%_1fr] lg:gap-6">
        <div className="motion-safe:animate-fade-up max-w-xl">
          <Badge tone="glass">
            <Sparkles className="h-3.5 w-3.5" strokeWidth={1.75} />
            AI-Powered Interview Practice
          </Badge>

          <h1 className="mt-5 text-5xl font-extrabold leading-[1.02] tracking-tight text-ink sm:text-6xl lg:text-[3.4rem] xl:text-7xl">
            Real Interviews.
            <br />
            <span className="bg-gradient-to-r from-primary to-primary-2 bg-clip-text text-transparent">
              Real Growth.
            </span>
          </h1>

          <p className="mt-5 max-w-md text-base leading-relaxed text-muted sm:text-lg">
            Practice with an AI interviewer that adapts to your answers, asks role-specific questions, and gives
            detailed feedback. Now with a voice-first experience.
          </p>

          <div className="mt-7 flex flex-wrap items-center gap-4">
            <Button to="/interview/new" variant="primary" withArrow>
              Start a Free Interview
            </Button>
            <Button href="#interview-preview" variant="secondary">
              <Play className="h-4 w-4" fill="currentColor" stroke="none" />
              Watch Demo
            </Button>
          </div>

          <ul className="mt-6 flex flex-wrap gap-x-5 gap-y-2">
            {CAPABILITY_POINTS.map((point) => (
              <li key={point} className="flex items-center gap-1.5 text-sm text-ink/70">
                <Check className="h-3.5 w-3.5 text-primary" strokeWidth={2} />
                {point}
              </li>
            ))}
          </ul>
        </div>

        <div id="interview-preview" className="scroll-mt-8">
          <InterviewPreview />
        </div>
      </div>
    </section>
  )
}

export default HeroSection
