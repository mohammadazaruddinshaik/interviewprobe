import { Mic } from 'lucide-react'
import { VOICE_STATUS } from '../../../voice/voiceState.js'

const ACTIVE_STATUSES = [VOICE_STATUS.CANDIDATE_LISTENING, VOICE_STATUS.CANDIDATE_SPEAKING, VOICE_STATUS.PROCESSING]

// The candidate self-view: a small landscape tile floating over the
// interviewer frame, clearly secondary to it. `candidate.webp` is today's
// visual fallback (there is no camera stream); the markup is a plain
// <img> inside a fixed-ratio frame so a future live MediaStream could
// replace it without changing this layout. The visible mic status text
// lives once, in VoiceStatusBar — this tile only shows a silent activity
// dot so the same words never render twice.
function CandidateTile({ status }) {
  const isActive = ACTIVE_STATUSES.includes(status)

  return (
    <div
      className={`relative aspect-[4/3] w-full overflow-hidden rounded-2xl border-2 shadow-glass transition-colors duration-200 ${
        isActive ? 'border-primary' : 'border-white/80'
      }`}
    >
      <img
        src="/assets/people/candidate.webp"
        alt="You, on a video call"
        className="h-full w-full object-cover object-[center_28%]"
      />
      <span className="absolute bottom-1.5 left-1.5 flex items-center gap-1 rounded-full bg-ink-fixed/55 px-2 py-0.5 text-[11px] font-medium text-white backdrop-blur-sm">
        <Mic className="h-3 w-3" strokeWidth={2} aria-hidden="true" />
        You
      </span>
      <span
        aria-hidden="true"
        className={`absolute right-1.5 top-1.5 flex h-5 w-5 items-center justify-center rounded-full ${
          isActive ? 'bg-primary text-white' : 'bg-ink-fixed/45 text-white/70'
        }`}
      >
        <span className={`h-1.5 w-1.5 rounded-full bg-current ${isActive ? 'motion-safe:animate-pulse' : ''}`} />
      </span>
    </div>
  )
}

export default CandidateTile
