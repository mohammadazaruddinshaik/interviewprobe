import { Mic, MoreHorizontal, Video as VideoIcon, X } from 'lucide-react'
import { NeuralChipIcon } from '../ui/interviewIcons.jsx'

// The Setup page's own interview-preview composition — deliberately NOT a
// smaller copy of the Landing page's wide video-call dashboard. This is a
// single, tall, image-led panel: the interviewer portrait is the primary
// visual, the AI-Interviewer status is fused directly to the bottom of
// the same frame (not a separate floating card), and the whole thing
// reads as "a preview of the room you're about to enter" rather than a
// mini product screenshot. Purely presentational/static: no voice
// session, no network calls, no fabricated interview data.
function ControlButton({ children, tone = 'neutral', label }) {
  const toneClasses =
    tone === 'danger'
      ? 'bg-danger text-white hover:bg-danger/90'
      : tone === 'dark'
        ? 'bg-ink-fixed text-white hover:bg-ink-fixed/85'
        : 'border border-glass/80 bg-glass text-ink hover:bg-glass/90'
  return (
    <button
      type="button"
      aria-label={label}
      className={`flex h-7 w-7 items-center justify-center rounded-full transition-colors duration-200 ${toneClasses}`}
    >
      {children}
    </button>
  )
}

function InterviewPreview() {
  return (
    <div className="mx-auto flex w-full max-w-[270px] flex-col overflow-hidden rounded-[26px] border border-glass/70 bg-ink/5 shadow-glass-sm">
      <div className="relative">
        <img
          src="/assets/people/interviewer.webp"
          alt="AI interviewer on a video call"
          className="aspect-[3/4] w-full object-cover object-[center_16%]"
        />

        <div className="absolute right-3 top-3 flex flex-col items-center gap-1">
          <span className="h-11 w-11 overflow-hidden rounded-full border-2 border-glass/90 shadow-glass-sm">
            <img
              src="/assets/people/candidate.webp"
              alt="Candidate on a video call"
              className="h-full w-full object-cover object-top"
            />
          </span>
          <span className="rounded-full bg-black/40 px-1.5 py-0.5 text-[8px] font-medium text-white backdrop-blur-sm">
            You
          </span>
        </div>

        <div className="absolute bottom-3 left-1/2 flex -translate-x-1/2 items-center gap-1.5 rounded-full bg-glass/90 p-1.5 shadow-glass-sm backdrop-blur-sm">
          <ControlButton label="Microphone">
            <Mic className="h-3.5 w-3.5" strokeWidth={1.75} />
          </ControlButton>
          <ControlButton label="Camera">
            <VideoIcon className="h-3.5 w-3.5" strokeWidth={1.75} />
          </ControlButton>
          <ControlButton tone="dark" label="More options">
            <MoreHorizontal className="h-3.5 w-3.5" strokeWidth={1.75} />
          </ControlButton>
          <ControlButton tone="danger" label="End preview">
            <X className="h-3.5 w-3.5" strokeWidth={2} />
          </ControlButton>
        </div>
      </div>

      {/* AI-Interviewer status fused to the same frame — the Setup page's
          one distinguishing move away from Landing's separate floating
          status card. */}
      <div className="flex items-center gap-2.5 border-t border-glass/60 bg-glass/70 px-3.5 py-3">
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary-light text-primary">
          <NeuralChipIcon className="h-3.5 w-3.5" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-semibold leading-tight text-ink">AI Interviewer</p>
          <p className="truncate text-[11px] leading-tight text-muted">Listening &amp; adapting in real time</p>
        </div>
        <span className="flex items-end gap-[2px]" aria-hidden="true">
          {[5, 9, 6, 12, 8].map((height, index) => (
            <span
              key={index}
              className="w-[2px] animate-pulse rounded-full bg-primary/50"
              style={{ height: `${height}px`, animationDelay: `${index * 120}ms` }}
            />
          ))}
        </span>
      </div>
    </div>
  )
}

export default InterviewPreview
