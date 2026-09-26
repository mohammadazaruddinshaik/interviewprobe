import Badge from '../ui/Badge.jsx'
import Button from '../ui/Button.jsx'
import { PlayIcon, SparkIcon } from '../ui/icons.jsx'
import InterviewPreview from './InterviewPreview.jsx'

function Hero() {
  return (
    <section id="top" className="relative overflow-hidden pt-6 sm:pt-10">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -right-32 -top-32 h-[28rem] w-[28rem] rounded-full bg-primary-light/70 blur-3xl"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -left-40 top-72 h-72 w-72 rounded-full bg-primary-light-2/80 blur-3xl"
      />

      <div className="relative mx-auto grid max-w-7xl items-center gap-16 px-6 pb-20 pt-14 md:pb-28 md:pt-20 lg:grid-cols-[1.05fr_1fr] lg:gap-12">
        <div className="motion-safe:animate-fade-up max-w-xl">
          <Badge>
            <SparkIcon className="h-3.5 w-3.5" />
            AI-Powered Technical Interview Practice
          </Badge>

          <h1 className="mt-6 text-5xl font-semibold leading-[1.05] tracking-tight text-ink sm:text-6xl">
            Practice Like It&apos;s Real.
            <br />
            <span className="text-primary">Interview Like It Matters.</span>
          </h1>

          <p className="mt-6 max-w-md text-lg leading-relaxed text-muted">
            Practice realistic technical interviews with an adaptive AI interviewer that listens to your
            answers, asks meaningful follow-ups, and gives structured feedback.
          </p>

          <div className="mt-9 flex flex-wrap items-center gap-4">
            <Button to="/interview/new" variant="primary" withArrow>
              Start an Interview
            </Button>
            <Button href="#how-it-works" variant="secondary">
              <PlayIcon className="h-4 w-4" />
              See How It Works
            </Button>
          </div>
        </div>

        <InterviewPreview />
      </div>
    </section>
  )
}

export default Hero
