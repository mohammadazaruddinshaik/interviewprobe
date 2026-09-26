import GlassCard from '../ui/GlassCard.jsx'
import { CheckIcon, MicIcon, SparkIcon, StopIcon } from '../ui/icons.jsx'
import { INTERVIEWER } from '../interview/voice/interviewer.js'

// A real, product-specific preview of the InterviewProbe voice interview
// room — built from the same visual language (glass surfaces, initials
// avatars, pill controls) the actual room uses, never a screenshot or a
// stock dashboard image. Purely presentational/static: no voice session,
// no network calls, no real question data — every string here is
// illustrative copy, not a live transcript.
const PREVIEW_QUESTIONS = [
  {
    number: '01',
    done: true,
    text: 'How would you design a scalable retrieval system for a RAG application?',
  },
  {
    number: '02',
    done: false,
    text: 'How do you keep data consistent across distributed services?',
  },
]

function ControlDot({ children, tone = 'neutral' }) {
  const toneClasses =
    tone === 'danger'
      ? 'bg-danger text-white'
      : tone === 'dark'
        ? 'bg-ink text-white'
        : 'border border-white/80 bg-white text-ink'
  return (
    <span className={`flex h-9 w-9 items-center justify-center rounded-full ${toneClasses}`}>{children}</span>
  )
}

function InterviewPreview() {
  return (
    <div className="relative mx-auto w-full max-w-xl lg:max-w-none">
      <div
        aria-hidden="true"
        className="absolute -inset-6 -z-10 rounded-[3rem] bg-gradient-to-br from-primary-light via-primary-light-2 to-transparent blur-2xl"
      />

      <GlassCard className="motion-safe:animate-fade-up overflow-hidden p-3 sm:p-4">
        {/* Header: brand + live timer + End Interview, mirroring the real
            room's header without exposing any internal mechanics. */}
        <div className="flex items-center justify-between gap-3 px-2 pb-3 sm:px-3">
          <div className="flex items-center gap-1.5 text-ink">
            <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-primary text-white">
              <SparkIcon className="h-3.5 w-3.5" />
            </span>
            <span className="text-sm font-semibold tracking-tight">InterviewProbe</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="hidden rounded-full bg-white/70 px-3 py-1 text-xs font-medium text-muted sm:inline-flex">
              24:36
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-danger/10 px-3 py-1 text-xs font-semibold text-danger">
              <span className="h-1.5 w-1.5 rounded-full bg-danger" />
              End Interview
            </span>
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-[1.5fr_1fr]">
          {/* "Video" stage */}
          <div className="relative overflow-hidden rounded-[20px] bg-gradient-to-br from-primary-light-2 via-white to-primary-light-2/70 p-5 sm:p-6">
            <div className="flex flex-col items-center gap-3 py-4 text-center">
              <span className="flex h-16 w-16 items-center justify-center rounded-full border-2 border-primary/25 bg-white text-lg font-semibold text-primary sm:h-20 sm:w-20 sm:text-xl">
                {INTERVIEWER.initials}
              </span>
              <div>
                <p className="text-sm font-semibold text-ink">{INTERVIEWER.name}</p>
                <p className="text-xs text-muted">{INTERVIEWER.role}</p>
              </div>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-white/80 px-3 py-1 text-xs font-medium text-primary">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary" />
                Speaking
              </span>
            </div>

            {/* Candidate tile */}
            <div className="absolute right-3 top-3 flex items-center gap-2 rounded-2xl border border-white/80 bg-white/90 px-2.5 py-2 shadow-glass-sm">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-light text-xs font-semibold text-primary">
                You
              </span>
              <span className="hidden text-xs font-medium text-muted sm:inline">Listening…</span>
            </div>

            {/* Control bar */}
            <div className="mt-4 flex items-center justify-center gap-2.5">
              <ControlDot>
                <MicIcon className="h-4 w-4" />
              </ControlDot>
              <ControlDot tone="dark">
                <SparkIcon className="h-4 w-4" />
              </ControlDot>
              <ControlDot tone="danger">
                <StopIcon className="h-3.5 w-3.5" />
              </ControlDot>
            </div>
          </div>

          {/* Question sidebar */}
          <div className="flex flex-col gap-2">
            <p className="px-1 text-xs font-semibold uppercase tracking-wide text-muted">Questions</p>
            {PREVIEW_QUESTIONS.map((question) => (
              <div
                key={question.number}
                className={`flex items-start gap-2.5 rounded-2xl border p-3 ${
                  question.done ? 'border-white/70 bg-white/70' : 'border-primary/20 bg-primary-light/50'
                }`}
              >
                <span
                  className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold ${
                    question.done ? 'bg-success/15 text-success' : 'bg-primary text-white'
                  }`}
                >
                  {question.done ? <CheckIcon className="h-3 w-3" /> : question.number}
                </span>
                <p className="text-xs leading-snug text-ink/80">{question.text}</p>
              </div>
            ))}
          </div>
        </div>

        {/* AI interviewer status strip */}
        <div className="mt-3 flex items-center gap-2.5 rounded-2xl bg-primary-light/60 px-4 py-3">
          <SparkIcon className="h-4 w-4 shrink-0 text-primary" />
          <p className="text-xs font-medium text-ink/80">
            <span className="font-semibold text-primary">AI Interviewer</span> — asking a follow-up based on your
            last answer…
          </p>
        </div>
      </GlassCard>
    </div>
  )
}

export default InterviewPreview
