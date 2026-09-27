import { Mic } from 'lucide-react'
import { VOICE_STATUS } from '../../../voice/voiceState.js'

// The exact candidate-facing microphone status this room has always
// shown, in a prominent bar rather than a small inline dot+label — the
// one place this room visibly names what the mic is doing right now.
const STATUS_COPY = {
  [VOICE_STATUS.CANDIDATE_LISTENING]: {
    label: 'Listening for your answer',
    hint: "Speak naturally — I'll transcribe in real time.",
  },
  [VOICE_STATUS.CANDIDATE_SPEAKING]: { label: 'Hearing you', hint: "Speak naturally — I'll transcribe in real time." },
  [VOICE_STATUS.PROCESSING]: { label: 'Processing your answer…', hint: 'Finishing up the transcript.' },
}

const ACTIVE_STATUSES = [VOICE_STATUS.CANDIDATE_LISTENING, VOICE_STATUS.CANDIDATE_SPEAKING, VOICE_STATUS.PROCESSING]

// Reacts to the real voice state only — a handful of static bar heights
// that pulse together while active is a deliberate, restrained stand-in
// for a live waveform (no audio-analysis library), and every bar freezes
// under `prefers-reduced-motion` via the existing global rule.
function VoiceWaveform({ active }) {
  const heights = [6, 11, 8, 14, 7, 12, 6]
  return (
    <span className="flex items-end gap-[3px]" aria-hidden="true">
      {heights.map((height, index) => (
        <span
          key={index}
          className={`w-[3px] rounded-full ${active ? 'bg-primary motion-safe:animate-pulse' : 'bg-line'}`}
          style={{ height: `${height}px`, animationDelay: `${index * 90}ms` }}
        />
      ))}
    </span>
  )
}

function VoiceStatusBar({ status }) {
  const isActive = ACTIVE_STATUSES.includes(status)
  const copy = STATUS_COPY[status] ?? { label: 'Microphone idle', hint: 'Press Speak Answer to begin.' }

  return (
    <div
      className={`flex items-center gap-3 rounded-2xl border px-4 py-3 transition-colors duration-200 ${
        isActive ? 'border-primary/30 bg-primary-light/40' : 'border-glass/70 bg-glass/60'
      }`}
    >
      <span
        className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full ${
          isActive ? 'bg-primary text-white' : 'bg-glass text-muted'
        }`}
      >
        <Mic className="h-4 w-4" strokeWidth={1.75} />
      </span>
      <div className="min-w-0 flex-1">
        <p role="status" aria-live="polite" className={`text-sm font-semibold ${isActive ? 'text-primary' : 'text-ink'}`}>
          {copy.label}
        </p>
        <p className="truncate text-xs text-muted">{copy.hint}</p>
      </div>
      <VoiceWaveform active={isActive} />
    </div>
  )
}

export default VoiceStatusBar
