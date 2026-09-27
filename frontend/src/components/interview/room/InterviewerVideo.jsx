import { NeuralChipIcon } from '../../ui/interviewIcons.jsx'
import CandidateTile from './CandidateTile.jsx'

// The room's visual focal point — a real, landscape video-call frame
// built from the actual production photo (never a generated avatar,
// screenshot, or initials badge), with the candidate's own tile floating
// over it, exactly as a real video call composes the two participants.
function InterviewerVideo({ interviewer, isSpeaking, status }) {
  return (
    <div className="relative overflow-hidden rounded-[26px] border border-glass/70 bg-ink/5 shadow-glass-sm">
      <img
        src="/assets/people/interviewer.webp"
        alt={`${interviewer.name}, AI interviewer, on a video call`}
        className="aspect-[16/10] w-full object-cover object-[center_18%] sm:aspect-[16/9]"
      />

      <span className="absolute left-3 top-3 flex items-center gap-2 rounded-full bg-black/40 py-1.5 pl-1.5 pr-3 text-white backdrop-blur-sm sm:left-4 sm:top-4">
        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary">
          <NeuralChipIcon className="h-3 w-3 text-white" />
        </span>
        <span className="leading-tight">
          <span className="block text-xs font-semibold">{interviewer.name}</span>
          <span className="block text-[10px] text-white/70">{interviewer.role}</span>
        </span>
      </span>

      <div className="absolute right-3 top-3 sm:right-4 sm:top-4">
        <CandidateTile status={status} />
      </div>

      {/* The exact "Interviewer speaking"/"Interviewer idle" text this room
          has always rendered — visually restyled as a floating pill over
          the video (matching the reference's status pill), but the same
          accessible copy, never an internal state name. */}
      <p
        role="status"
        aria-live="polite"
        className={`absolute bottom-3 left-1/2 inline-flex -translate-x-1/2 items-center gap-2 rounded-full px-4 py-2 text-sm font-medium text-white shadow-glass-sm backdrop-blur-sm transition-colors duration-200 sm:bottom-4 ${
          isSpeaking ? 'bg-primary/90' : 'bg-black/35'
        }`}
      >
        <span
          aria-hidden="true"
          className={`h-1.5 w-1.5 rounded-full bg-white ${isSpeaking ? 'motion-safe:animate-pulse' : 'opacity-60'}`}
        />
        {isSpeaking ? 'Interviewer speaking' : 'Interviewer idle'}
      </p>
    </div>
  )
}

export default InterviewerVideo
