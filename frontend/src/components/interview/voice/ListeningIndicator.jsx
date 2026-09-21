import { VOICE_STATUS } from '../../../voice/voiceState.js'

const STATUS_LABEL = {
  [VOICE_STATUS.CANDIDATE_LISTENING]: 'Listening for your answer',
  [VOICE_STATUS.CANDIDATE_SPEAKING]: 'Hearing you',
  [VOICE_STATUS.PROCESSING]: 'Processing your answer…',
}

const ACTIVE_STATUSES = [VOICE_STATUS.CANDIDATE_LISTENING, VOICE_STATUS.CANDIDATE_SPEAKING, VOICE_STATUS.PROCESSING]

// Reads the session's raw status (not the collapsed micUiState) so it can
// tell listening/speaking/processing apart, per the room's four distinct
// candidate states — this only reads existing state, it doesn't add any.
function ListeningIndicator({ status }) {
  const active = ACTIVE_STATUSES.includes(status)
  const label = STATUS_LABEL[status] ?? 'Microphone idle'

  return (
    <p
      role="status"
      aria-live="polite"
      className={`inline-flex items-center gap-1.5 text-xs font-medium ${active ? 'text-accent' : 'text-muted'}`}
    >
      <span
        aria-hidden="true"
        className={`h-1.5 w-1.5 rounded-full ${active ? 'bg-accent motion-safe:animate-pulse' : 'bg-line'}`}
      />
      {label}
    </p>
  )
}

export default ListeningIndicator
