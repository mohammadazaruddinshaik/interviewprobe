import { Mic, PhoneOff } from 'lucide-react'
import { InterviewerIcon } from '../ui/interviewIcons.jsx'

// A glimpse of the product, not the product compressed into a card: the
// interviewer (the primary subject, a 16:9 frame with room around the
// face), a small candidate self-view, the current question, and a quiet
// voice status. Static illustration only — nothing animates here because
// nothing is actually live, and the controls are drawn shapes
// (aria-hidden), not buttons.
function ControlGlyph({ children, tone = 'light' }) {
  return (
    <span
      className={`flex h-8 w-8 items-center justify-center rounded-full ${
        tone === 'danger' ? 'bg-danger text-white' : 'border border-line bg-glass text-ink'
      }`}
    >
      {children}
    </span>
  )
}

function InterviewPreview() {
  return (
    <div
      aria-hidden="true"
      className="motion-safe:animate-fade-up w-full max-w-[560px] rounded-[var(--radius-shell)] border border-glass/70 bg-glass/60 p-3 shadow-glass-lg backdrop-blur-xl"
    >
      <div className="relative aspect-[16/9] overflow-hidden rounded-[var(--radius-panel)] bg-ink/5">
        <img
          src="/assets/people/interviewer.webp"
          alt=""
          className="absolute inset-0 h-full w-full object-cover object-[center_22%]"
        />

        <span className="absolute left-3 top-3 flex items-center gap-1.5 rounded-full bg-ink-fixed/40 px-2.5 py-1 text-xs font-medium text-white backdrop-blur-md">
          <InterviewerIcon className="h-3.5 w-3.5" />
          AI Interviewer
        </span>

        <div className="absolute right-3 top-3 aspect-[4/3] w-[26%] overflow-hidden rounded-xl border-2 border-white/80 shadow-glass-sm">
          <img src="/assets/people/candidate.webp" alt="" className="h-full w-full object-cover object-[center_28%]" />
          <span className="absolute bottom-1 left-1.5 text-[10px] font-medium text-white drop-shadow">You</span>
        </div>
      </div>

      <div className="px-2 pt-2.5">
        <p className="text-xs font-medium text-muted">Current question</p>
        <p className="mt-1 text-[15px] font-semibold leading-snug text-ink">
          How would you design a rate limiter for a public API?
        </p>

        <div className="mt-2.5 flex items-center justify-between gap-3 border-t border-line pt-2.5">
          <span className="flex items-center gap-2 text-xs font-medium text-primary">
            <span className="flex items-center gap-[2px]">
              {[4, 8, 5, 10, 6].map((height, index) => (
                <span key={index} className="w-[2px] rounded-full bg-current" style={{ height: `${height}px` }} />
              ))}
            </span>
            Listening to your answer
          </span>
          <span className="flex items-center gap-2">
            <ControlGlyph>
              <Mic className="h-3.5 w-3.5" strokeWidth={1.75} />
            </ControlGlyph>
            <ControlGlyph tone="danger">
              <PhoneOff className="h-3.5 w-3.5" strokeWidth={1.75} />
            </ControlGlyph>
          </span>
        </div>
      </div>
    </div>
  )
}

export default InterviewPreview
