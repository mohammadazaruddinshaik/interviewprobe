import { Video, VideoOff } from 'lucide-react'
import { useCandidateCamera } from '../../../hooks/useCandidateCamera.js'
import { VOICE_STATUS } from '../../../voice/voiceState.js'

const ACTIVE_STATUSES = [VOICE_STATUS.CANDIDATE_LISTENING, VOICE_STATUS.CANDIDATE_SPEAKING, VOICE_STATUS.PROCESSING]

// The candidate's own small self-view, secondary to the interviewer beside
// it. Camera is entirely optional and self-contained (useCandidateCamera):
// off by default, toggled with the button below the tile (always visible
// and a real touch target — never a hover-only affordance), and never
// required. When on, this shows the real getUserMedia stream (muted,
// mirrored like any self-view); every other state — off, still requesting
// permission, denied, or no camera hardware at all — falls back to the
// same static production photo, and voice keeps working identically
// either way.
function CandidateTile({ status }) {
  const isActive = ACTIVE_STATUSES.includes(status)
  const { state: cameraState, videoRef, toggle: toggleCamera } = useCandidateCamera()
  const isLive = cameraState === 'on'

  return (
    <div className="flex shrink-0 flex-col items-center gap-1">
      <div
        className={`relative h-14 w-14 overflow-hidden rounded-full border shadow-glass-sm transition-colors duration-200 sm:h-16 sm:w-16 ${
          isActive ? 'border-primary' : 'border-glass/70'
        }`}
      >
        {isLive ? (
          <video ref={videoRef} autoPlay playsInline muted className="h-full w-full scale-x-[-1] object-cover" />
        ) : (
          <img
            src="/assets/people/candidate.webp"
            alt="You"
            className="h-full w-full object-cover object-[center_28%]"
          />
        )}

        <span
          aria-hidden="true"
          className={`absolute right-0.5 top-0.5 flex h-3.5 w-3.5 items-center justify-center rounded-full ${
            isActive ? 'bg-primary' : 'bg-ink-fixed/40'
          }`}
        >
          <span className={`h-1.5 w-1.5 rounded-full bg-white ${isActive ? 'motion-safe:animate-pulse' : 'opacity-70'}`} />
        </span>
      </div>

      <div className="flex items-center gap-1">
        <span className="text-[11px] font-medium text-muted">You</span>
        <button
          type="button"
          onClick={toggleCamera}
          aria-pressed={isLive}
          aria-label={isLive ? 'Turn camera off' : 'Turn camera on'}
          title={cameraState === 'denied' ? 'Camera unavailable — check your browser permissions' : undefined}
          className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full border transition-colors duration-150 ${
            isLive ? 'border-primary/40 bg-primary-light text-primary' : 'border-line text-muted hover:text-ink'
          }`}
        >
          {isLive ? <Video className="h-3 w-3" strokeWidth={2} /> : <VideoOff className="h-3 w-3" strokeWidth={2} />}
        </button>
      </div>
    </div>
  )
}

export default CandidateTile
