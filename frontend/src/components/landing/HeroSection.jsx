import { Play } from 'lucide-react'
import Button from '../ui/Button.jsx'
import { InterviewerIcon } from '../ui/interviewIcons.jsx'
import InterviewPreview from './InterviewPreview.jsx'

function HeroSection() {
  return (
    <section id="top" className="scroll-mt-28 px-4 pb-12 pt-10 sm:px-6 sm:pt-14 lg:px-10 lg:pb-16 lg:pt-16">
      <div className="mx-auto grid max-w-[1280px] items-center gap-10 lg:grid-cols-[minmax(0,0.86fr)_minmax(0,1fr)] lg:gap-14">
        <div className="motion-safe:animate-fade-up min-w-0">
          <span className="inline-flex items-center gap-2 rounded-full border border-glass/70 bg-glass/70 px-3.5 py-1.5 text-sm font-medium text-primary shadow-glass-sm">
            <InterviewerIcon className="h-4 w-4" />
            AI-Powered Technical Interviews
          </span>

          <h1 className="mt-6 text-[2.9rem] font-extrabold leading-[1.02] tracking-[-0.035em] text-ink sm:text-6xl lg:text-[4.1rem] xl:text-[4.75rem]">
            Real Interviews.
            <br />
            <span className="bg-gradient-to-r from-primary to-accent-2 bg-clip-text text-transparent">Real Growth.</span>
          </h1>

          <p className="mt-6 max-w-[34rem] text-base leading-relaxed text-muted sm:text-lg">
            Practice with an AI interviewer that adapts to your role, asks realistic technical questions, and helps
            you improve with detailed feedback.
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-3 sm:gap-4">
            <Button to="/interview/new" variant="primary" withArrow className="px-7 py-3.5 text-base">
              Start a Free Interview
            </Button>
            {/* There is no recorded video — this scrolls to the product
                preview on this page, which is what it actually shows. */}
            <Button href="#interview-preview" variant="secondary" className="px-6 py-3.5 text-base">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary-light text-primary">
                <Play className="h-3 w-3 translate-x-px" fill="currentColor" stroke="none" />
              </span>
              Watch Demo
            </Button>
          </div>
        </div>

        <div id="interview-preview" className="flex min-w-0 scroll-mt-28 justify-center lg:justify-end">
          <InterviewPreview />
        </div>
      </div>
    </section>
  )
}

export default HeroSection
