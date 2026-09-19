import Button from '../ui/Button.jsx'
import { CheckIcon, PlayIcon } from '../ui/icons.jsx'

const SUPPORTING_POINTS = [
  'Multiple technical roles',
  'Adaptive questioning',
  'Evidence-based feedback',
]

function Hero() {
  return (
    <section id="top" className="relative overflow-hidden">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -right-40 -top-40 h-[32rem] w-[32rem] rounded-full bg-accent-soft/70 blur-3xl"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute right-10 top-64 h-72 w-72 rounded-full bg-accent-softer blur-3xl"
      />

      <div className="relative mx-auto grid max-w-7xl items-center gap-16 px-6 pb-20 pt-16 md:pb-28 md:pt-24 lg:grid-cols-[1.05fr_1fr] lg:gap-12">
        <div className="max-w-xl">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent">
            Practice &bull; Improve &bull; Get hired
          </p>

          <h1 className="mt-5 text-5xl font-semibold leading-[1.05] tracking-tight text-ink sm:text-6xl">
            Real interviews.
            <br />
            <span className="text-accent">Real preparation.</span>
          </h1>

          <p className="mt-6 max-w-md text-lg leading-relaxed text-muted">
            Practice realistic technical interviews with adaptive questions and detailed
            feedback — so your first real interview doesn&apos;t have to be your first real
            practice.
          </p>

          <div className="mt-9 flex flex-wrap items-center gap-4">
            <Button to="/interview/new" variant="primary" withArrow>
              Start an interview
            </Button>
            <Button href="#how-it-works" variant="secondary">
              <PlayIcon className="h-4 w-4" />
              See how it works
            </Button>
          </div>

          <ul className="mt-10 flex flex-wrap gap-x-6 gap-y-2">
            {SUPPORTING_POINTS.map((point) => (
              <li key={point} className="flex items-center gap-1.5 text-sm text-ink/60">
                <CheckIcon className="h-3.5 w-3.5 text-accent" />
                {point}
              </li>
            ))}
          </ul>
        </div>

        <div className="relative mx-auto w-full max-w-lg lg:max-w-none">
          <div
            aria-hidden="true"
            className="absolute inset-x-6 -inset-y-6 -z-10 rounded-[2.5rem] bg-gradient-to-br from-accent-soft via-accent-softer to-transparent blur-2xl"
          />
          <img
            src="/images/interviewprobe-preview.png"
            alt="InterviewProbe interview screen showing an adaptive AI Engineer question on retrieval-augmented generation, with topic progress and an answer editor"
            width={1536}
            height={1024}
            loading="eager"
            decoding="async"
            className="motion-safe:animate-float w-full rounded-2xl border border-line/60 shadow-2xl shadow-ink/10"
          />
        </div>
      </div>
    </section>
  )
}

export default Hero
