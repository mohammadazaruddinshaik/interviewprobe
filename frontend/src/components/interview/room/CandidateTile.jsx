import { VOICE_STATUS } from '../../../voice/voiceState.js'

const ACTIVE_STATUSES = [VOICE_STATUS.CANDIDATE_LISTENING, VOICE_STATUS.CANDIDATE_SPEAKING, VOICE_STATUS.PROCESSING]

// Substantially smaller than the interviewer video and floating over it —
// the candidate self-view. `candidate.webp` is today's visual fallback;
// the markup is a plain <img> inside a fixed-size frame specifically so a
// future live MediaStream can replace the <img> without changing this
// component's layout/sizing contract. The visible "Listening for your
// answer"/etc. text lives once, in VoiceStatusBar below the video — this
// tile only shows a small silent pulse dot, to avoid rendering that same
// status text twice on screen.
function CandidateTile({ status }) {
  const isActive = ACTIVE_STATUSES.includes(status)

  return (
    <div className="flex flex-col items-end gap-1">
      <div className="relative h-16 w-16 overflow-hidden rounded-2xl border-2 border-glass/90 shadow-glass-sm sm:h-20 sm:w-20">
        <img src="/assets/people/candidate.webp" alt="You, on a video call" className="h-full w-full object-cover object-top" />
        <span className="absolute bottom-1 left-1 rounded bg-black/50 px-1 text-[9px] font-medium text-white">You</span>
        <span
          aria-hidden="true"
          className={`absolute right-1 top-1 flex h-4 w-4 items-center justify-center rounded-full bg-black/50 ${isActive ? 'text-primary-light' : 'text-white/60'}`}
        >
          <span className={`h-1.5 w-1.5 rounded-full bg-current ${isActive ? 'motion-safe:animate-pulse' : ''}`} />
        </span>
      </div>
    </div>
  )
}

export default CandidateTile
