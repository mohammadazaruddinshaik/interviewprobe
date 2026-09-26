import { Check, Mic, MoreHorizontal, Sparkles, Square, Video as VideoIcon, MessageSquare } from 'lucide-react'
import GlassCard from '../ui/GlassCard.jsx'

// A real, product-specific preview of the InterviewProbe interview room —
// built from real HTML/React (never a screenshot), using the actual
// production people photos (public/assets/people) and brand mark, so it
// reads as a believable screenshot of the real product rather than a
// generic stock dashboard. Purely presentational/static: no voice session,
// no network calls — every string here is illustrative marketing copy.
const PREVIEW_TABS = ['Interview', 'Progress', 'Feedback', 'Resources']
const PANEL_TABS = ['Question', 'Transcript', 'Feedback']

const PREVIEW_QUESTIONS = [
  {
    number: '01',
    done: true,
    title: 'How would you design a scalable notification system?',
    description: 'Discuss architecture, trade-offs, and how you would handle high throughput and reliability.',
  },
  {
    number: '02',
    done: false,
    title: 'How do you ensure data consistency in distributed systems?',
  },
]

function ControlButton({ children, tone = 'neutral', label }) {
  const toneClasses =
    tone === 'danger'
      ? 'bg-danger text-white hover:bg-danger/90'
      : tone === 'dark'
        ? 'bg-ink text-white hover:bg-ink/85'
        : 'border border-white/80 bg-white text-ink hover:bg-white/90'
  return (
    <button
      type="button"
      aria-label={label}
      className={`flex h-10 w-10 items-center justify-center rounded-full transition-colors duration-200 ${toneClasses}`}
    >
      {children}
    </button>
  )
}

function InterviewPreview() {
  return (
    <div className="motion-safe:animate-fade-up relative mx-auto w-full max-w-2xl [animation-delay:150ms] lg:max-w-none">
      <GlassCard className="overflow-hidden p-4 sm:p-6">
        {/* Header: brand + section tabs + timer + End Interview — generous
            horizontal rhythm rather than everything crammed edge to edge. */}
        <div className="flex flex-wrap items-center justify-between gap-4 pb-5">
          <div className="flex items-center gap-2 text-ink">
            <img src="/assets/brand/logo-icon.svg" alt="" aria-hidden="true" className="h-5 w-5" />
            <span className="text-sm font-semibold tracking-tight">InterviewProbe</span>
          </div>

          <nav
            className="hidden items-center gap-6 text-xs font-medium text-muted md:flex"
            aria-label="Interview room sections"
          >
            {PREVIEW_TABS.map((tab, index) => (
              <span key={tab} className={index === 0 ? 'text-primary' : ''}>
                {tab}
              </span>
            ))}
          </nav>

          <div className="flex items-center gap-2.5">
            <span className="rounded-full bg-white/70 px-3.5 py-1.5 text-xs font-medium text-muted">24:36</span>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-danger px-3.5 py-1.5 text-xs font-semibold text-white">
              <Square className="h-3 w-3" strokeWidth={2.25} fill="currentColor" />
              End Interview
            </span>
          </div>
        </div>

        {/* Main body: ~62/38 video/panel split, with real breathing room
            between the two columns rather than a tight dashboard grid. */}
        <div className="grid items-start gap-5 lg:grid-cols-[1.65fr_1fr]">
          {/* Video stage — real interviewer photo, natural framing (head,
              shoulders, headset, and background all visible — not a tight
              face crop), candidate photo floating above it. `items-start`
              on the grid (rather than the default stretch) keeps this
              card exactly as tall as the image itself — without it, grid
              stretches this cell to match the taller question panel,
              leaving empty space below the photo that the absolutely-
              positioned control bar would float into instead of the
              image's true bottom edge. */}
          <div className="relative self-start overflow-hidden rounded-[24px] border border-white/70 bg-ink/5 shadow-glass-sm">
            <img
              src="/assets/people/interviewer.webp"
              alt="AI interviewer on a video call"
              className="aspect-[4/3] w-full object-cover object-[center_18%]"
            />

            <div className="absolute right-4 top-4 h-[4.5rem] w-24 overflow-hidden rounded-2xl border-2 border-white/90 shadow-glass-sm">
              <img
                src="/assets/people/candidate.webp"
                alt="Candidate on a video call"
                className="h-full w-full object-cover object-top"
              />
              <span className="absolute bottom-1 right-1 flex h-4 w-4 items-center justify-center rounded-full bg-white/90">
                <span className="flex items-end gap-px" aria-hidden="true">
                  <span className="w-[1.5px] animate-pulse rounded-full bg-primary" style={{ height: '3px' }} />
                  <span
                    className="w-[1.5px] animate-pulse rounded-full bg-primary"
                    style={{ height: '6px', animationDelay: '150ms' }}
                  />
                  <span
                    className="w-[1.5px] animate-pulse rounded-full bg-primary"
                    style={{ height: '4px', animationDelay: '300ms' }}
                  />
                </span>
              </span>
            </div>

            <div className="absolute bottom-4 left-1/2 flex -translate-x-1/2 items-center gap-2.5 rounded-full bg-white/90 p-2 shadow-glass-sm backdrop-blur-sm">
              <ControlButton label="Microphone">
                <Mic className="h-4 w-4" strokeWidth={1.75} />
              </ControlButton>
              <ControlButton label="Camera">
                <VideoIcon className="h-4 w-4" strokeWidth={1.75} />
              </ControlButton>
              <ControlButton label="Transcript">
                <MessageSquare className="h-4 w-4" strokeWidth={1.75} />
              </ControlButton>
              <ControlButton tone="dark" label="More options">
                <MoreHorizontal className="h-4 w-4" strokeWidth={1.75} />
              </ControlButton>
              <ControlButton tone="danger" label="End interview">
                <Square className="h-3.5 w-3.5" strokeWidth={2} fill="currentColor" />
              </ControlButton>
            </div>
          </div>

          {/* Question sidebar */}
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-4 border-b border-line px-1 pb-2.5 text-xs font-semibold text-muted">
              {PANEL_TABS.map((tab, index) => (
                <span key={tab} className={index === 0 ? 'text-ink' : ''}>
                  {tab}
                </span>
              ))}
            </div>
            {PREVIEW_QUESTIONS.map((question) => (
              <div
                key={question.number}
                className={`flex flex-col gap-2 rounded-2xl border p-4 ${
                  question.done ? 'border-white/70 bg-white/70' : 'border-primary/20 bg-primary-light/50'
                }`}
              >
                <span
                  className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold ${
                    question.done ? 'bg-success/15 text-success' : 'bg-primary text-white'
                  }`}
                >
                  {question.done ? <Check className="h-3 w-3" strokeWidth={2.5} /> : question.number}
                </span>
                <div>
                  <p className="text-sm font-semibold leading-snug text-ink">{question.title}</p>
                  {question.description && (
                    <p className="mt-1.5 text-xs leading-relaxed text-muted">{question.description}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* AI interviewer status strip — a real, generously-sized part of
            the interface, not a thin notification. */}
        <div className="mt-5 flex items-center gap-3 rounded-2xl bg-primary-light/60 px-5 py-4">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/80 text-primary">
            <Sparkles className="h-4 w-4" strokeWidth={1.75} />
          </span>
          <p className="text-sm font-medium text-ink/80">
            <span className="font-semibold text-primary">AI Interviewer</span> — asking follow-up questions based on
            your answers…
          </p>
          <span className="ml-auto flex items-end gap-0.5" aria-hidden="true">
            {[5, 10, 7, 13, 6].map((height, index) => (
              <span
                key={index}
                className="w-[3px] animate-pulse rounded-full bg-primary/50"
                style={{ height: `${height}px`, animationDelay: `${index * 120}ms` }}
              />
            ))}
          </span>
        </div>
      </GlassCard>
    </div>
  )
}

export default InterviewPreview
