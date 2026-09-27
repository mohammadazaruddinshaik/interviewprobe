import { Play } from 'lucide-react'
import Badge from '../ui/Badge.jsx'
import Button from '../ui/Button.jsx'
import { NeuralChipIcon } from '../ui/interviewIcons.jsx'
import InterviewPreview from './InterviewPreview.jsx'

function HeroSection() {
  return (
    <section id="top" className="scroll-mt-4 px-4 pb-8 pt-6 sm:px-6 sm:pb-10 sm:pt-8 lg:px-10 lg:pb-12 lg:pt-10">
      <div className="grid items-center gap-8 lg:grid-cols-[43%_1fr] lg:gap-6">
        <div className="motion-safe:animate-fade-up max-w-xl">
          <Badge tone="glass">
            <NeuralChipIcon className="h-3.5 w-3.5" />
            AI-Powered Technical Interviews
          </Badge>

          <h1 className="mt-5 text-5xl font-extrabold leading-[1.02] tracking-tight text-ink sm:text-6xl lg:text-[3.4rem] xl:text-7xl">
            Real Interviews.
            <br />
            <span className="bg-gradient-to-r from-primary to-primary-2 bg-clip-text text-transparent">
              Real Growth.
            </span>
          </h1>

          <p className="mt-5 max-w-md text-base leading-relaxed text-muted sm:text-lg">
            Practice with an AI interviewer that adapts to your answers, asks realistic technical questions, and
            helps you improve.
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-4">
            <Button to="/interview/new" variant="primary" withArrow>
              Start a Free Interview
            </Button>
            <Button href="#interview-preview" variant="secondary">
              <Play className="h-4 w-4" fill="currentColor" stroke="none" />
              Watch Demo
            </Button>
          </div>
        </div>

        <div id="interview-preview" className="scroll-mt-8">
          <InterviewPreview />
        </div>
      </div>
    </section>
  )
}

export default HeroSection
