import { InterviewerIcon } from '../../ui/interviewIcons.jsx'

// A restrained "presence ring" around the portrait while the interviewer
// is actually speaking — state-driven, not decorative: it only appears
// for as long as INTERVIEWER_SPEAKING is true, and holds still otherwise.
function PresenceRing({ active }) {
  return (
    <span
      aria-hidden="true"
      className={`pointer-events-none absolute -inset-1.5 rounded-full border-2 transition-opacity duration-300 ${
        active ? 'border-primary/60 opacity-100 motion-safe:animate-pulse' : 'opacity-0'
      }`}
    />
  )
}

// The interviewer, deliberately small — a portrait, not a stage. The
// question is the room's visual focus; this exists to establish "a person
// is asking you this," then steps back. Uses the real production photo,
// never a generated avatar.
function InterviewerVideo({ interviewer, isSpeaking, className = '' }) {
  return (
    <div className={`flex min-w-0 items-center gap-3 ${className}`}>
      <div className="relative shrink-0">
        <PresenceRing active={isSpeaking} />
        <img
          src="/assets/people/interviewer.webp"
          alt={`${interviewer.name}, AI interviewer`}
          className="h-14 w-14 rounded-full border border-glass/70 object-cover object-[center_14%] shadow-glass-sm sm:h-16 sm:w-16"
        />
      </div>
      <div className="min-w-0">
        <p className="flex items-center gap-1.5 truncate text-sm font-semibold text-ink sm:text-base">
          <InterviewerIcon className="h-4 w-4 shrink-0 text-primary" />
          {interviewer.name}
        </p>
        <p className="truncate text-xs text-muted sm:text-[13px]">{interviewer.role}</p>
        {/* The exact "Interviewer speaking"/"Interviewer idle" text this
            room has always rendered, driven by the real speaker state —
            now a quiet inline line rather than a floating pill over a
            giant video frame. */}
        <p role="status" aria-live="polite" className="mt-0.5 flex items-center gap-1.5 text-xs font-medium">
          <span
            aria-hidden="true"
            className={`h-1.5 w-1.5 rounded-full ${isSpeaking ? 'bg-primary motion-safe:animate-pulse' : 'bg-line'}`}
          />
          <span className={isSpeaking ? 'text-primary' : 'text-muted'}>
            {isSpeaking ? 'Interviewer speaking' : 'Interviewer idle'}
          </span>
        </p>
      </div>
    </div>
  )
}

export default InterviewerVideo
