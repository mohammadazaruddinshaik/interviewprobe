import { InterviewerIcon } from '../../ui/interviewIcons.jsx'
import CandidateTile from './CandidateTile.jsx'

function SpeakingBars({ active }) {
  const heights = [5, 9, 13, 8, 11, 6]
  return (
    <span className="flex items-center gap-[2px]" aria-hidden="true">
      {heights.map((height, index) => (
        <span
          key={index}
          className={`w-[2px] rounded-full bg-white ${active ? 'motion-safe:animate-pulse' : 'opacity-60'}`}
          style={{ height: `${active ? height : 4}px`, animationDelay: `${index * 110}ms` }}
        />
      ))}
    </span>
  )
}

// The interviewer's video frame — a compact 16:9 stage. The portrait is
// shown whole (head, shoulders, hands) rather than cropped to fill the
// width, so the face has breathing room instead of taking over the frame;
// its left/right edges fade into a backdrop sampled from the photo itself
// (the --color-stage-* tokens), the way a meeting app frames a portrait
// camera. The candidate's self-view is a small secondary tile.
function InterviewerVideo({ interviewer, isSpeaking, status, className = '' }) {
  return (
    <div
      className={`relative aspect-video overflow-hidden rounded-[var(--radius-panel)] border border-glass/70 bg-gradient-to-b from-stage-1 via-stage-2 to-stage-3 shadow-glass-sm ${className}`}
    >
      <img
        src="/assets/people/interviewer.webp"
        alt={`${interviewer.name}, AI interviewer, on a video call`}
        className="absolute inset-y-0 left-1/2 h-full w-auto max-w-none -translate-x-1/2 [mask-image:linear-gradient(to_right,transparent,black_16%,black_84%,transparent)]"
      />

      <span className="absolute left-3 top-3 flex items-center gap-2 rounded-full bg-white/85 py-1 pl-2 pr-3 text-ink-fixed shadow-glass-sm backdrop-blur-md sm:left-4 sm:top-4">
        <InterviewerIcon className="h-4 w-4 text-primary" />
        <span className="leading-tight">
          <span className="block text-xs font-semibold sm:text-sm">{interviewer.name}</span>
          <span className="block text-[10px] text-ink-fixed/60 sm:text-[11px]">{interviewer.role}</span>
        </span>
      </span>

      <div className="absolute right-3 top-3 w-[22%] min-w-20 max-w-40 sm:right-4 sm:top-4">
        <CandidateTile status={status} />
      </div>

      {/* The exact "Interviewer speaking"/"Interviewer idle" text this room
          has always rendered, driven by the real speaker state; its bars
          only move while the interviewer is actually speaking. */}
      <p
        role="status"
        aria-live="polite"
        className={`absolute bottom-3 left-1/2 inline-flex -translate-x-1/2 items-center gap-2 whitespace-nowrap rounded-full px-3.5 py-1.5 text-xs font-medium text-white shadow-glass-sm backdrop-blur-md transition-colors duration-200 sm:bottom-4 sm:text-sm ${
          isSpeaking ? 'bg-primary/90' : 'bg-ink-fixed/45'
        }`}
      >
        <SpeakingBars active={isSpeaking} />
        {isSpeaking ? 'Interviewer speaking' : 'Interviewer idle'}
      </p>
    </div>
  )
}

export default InterviewerVideo
