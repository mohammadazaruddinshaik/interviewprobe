import { InterviewerIcon } from '../ui/interviewIcons.jsx'

// A small "who you'll be talking to" preview for the Setup page — a
// compact landscape frame, deliberately smaller than Landing's and far
// smaller than the live room's, so the same photo never dominates two
// pages in a row. The candidate's self-view is a small tile, and the
// status line underneath is static: nothing here is live, so nothing
// moves. Purely illustrative (aria-hidden).
function InterviewPreview() {
  return (
    <div
      aria-hidden="true"
      className="mx-auto w-full max-w-[300px] overflow-hidden xl:max-w-none rounded-[var(--radius-panel)] border border-glass/70 bg-glass/60 shadow-glass-sm"
    >
      <div className="relative aspect-[4/3]">
        <img
          src="/assets/people/interviewer.webp"
          alt=""
          className="absolute inset-0 h-full w-full object-cover object-[center_24%]"
        />
        <div className="absolute right-2.5 top-2.5 aspect-[4/3] w-[30%] overflow-hidden rounded-lg border-2 border-white/80 shadow-glass-sm">
          <img src="/assets/people/candidate.webp" alt="" className="h-full w-full object-cover object-[center_28%]" />
          <span className="absolute bottom-0.5 left-1 text-[9px] font-medium text-white drop-shadow">You</span>
        </div>
      </div>

      <div className="flex items-center gap-2.5 px-3.5 py-3">
        <InterviewerIcon className="h-4.5 w-4.5 shrink-0 text-primary" />
        <div className="min-w-0">
          <p className="text-xs font-semibold leading-tight text-ink">Your AI interviewer</p>
          <p className="truncate text-[11px] leading-tight text-muted">Asks aloud, listens, adapts to your answers</p>
        </div>
      </div>
    </div>
  )
}

export default InterviewPreview
