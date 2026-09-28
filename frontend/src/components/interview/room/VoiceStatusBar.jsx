import { useEffect, useState } from 'react'
import { Mic } from 'lucide-react'
import { VOICE_STATUS } from '../../../voice/voiceState.js'

// The exact candidate-facing microphone status this room has always
// shown — the one place it visibly names what the mic is doing now.
const STATUS_COPY = {
  [VOICE_STATUS.CANDIDATE_LISTENING]: {
    label: 'Listening for your answer',
    hint: "Speak naturally — I'll transcribe in real time.",
  },
  [VOICE_STATUS.CANDIDATE_SPEAKING]: { label: 'Hearing you', hint: "Speak naturally — I'll transcribe in real time." },
  [VOICE_STATUS.PROCESSING]: { label: 'Processing your answer…', hint: 'Finishing up the transcript.' },
}

const ACTIVE_STATUSES = [VOICE_STATUS.CANDIDATE_LISTENING, VOICE_STATUS.CANDIDATE_SPEAKING, VOICE_STATUS.PROCESSING]

// Reacts to the real voice state only — static bar heights that pulse
// together while active (no audio-analysis library); frozen under
// `prefers-reduced-motion` by the existing global rule.
function VoiceWaveform({ active }) {
  const heights = [6, 12, 9, 18, 11, 22, 14, 8, 16, 10, 6]
  return (
    <span className="hidden items-center gap-[3px] sm:flex xl:hidden 2xl:flex" aria-hidden="true">
      {heights.map((height, index) => (
        <span
          key={index}
          className={`w-[3px] rounded-full ${active ? 'bg-primary motion-safe:animate-pulse' : 'bg-line'}`}
          style={{ height: `${active ? height : Math.max(4, height / 3)}px`, animationDelay: `${index * 80}ms` }}
        />
      ))}
    </span>
  )
}

// How long the mic has been open for this answer — measured here, from
// the moment the real voice state became active; hidden while idle.
function useActiveSeconds(active) {
  const [seconds, setSeconds] = useState(0)

  useEffect(() => {
    if (!active) return undefined
    const startedAt = Date.now()
    const id = setInterval(() => setSeconds(Math.floor((Date.now() - startedAt) / 1000)), 1000)
    return () => {
      clearInterval(id)
      setSeconds(0)
    }
  }, [active])

  return seconds
}

function formatSeconds(total) {
  return `${String(Math.floor(total / 60)).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`
}

function VoiceStatusBar({ status }) {
  const isActive = ACTIVE_STATUSES.includes(status)
  const copy = STATUS_COPY[status] ?? { label: 'Microphone idle', hint: 'Press Speak answer to begin.' }
  const activeSeconds = useActiveSeconds(isActive)

  return (
    <div
      className={`flex shrink-0 items-center gap-3 rounded-full border py-2 pl-2 pr-4 shadow-glass-sm transition-colors duration-200 sm:gap-4 sm:pr-5 ${
        isActive ? 'border-primary/25 bg-primary-light/60' : 'border-glass/70 bg-glass/60'
      }`}
    >
      <span
        className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${
          isActive ? 'bg-primary text-white shadow-glass-sm' : 'bg-glass text-muted'
        }`}
      >
        <Mic className="h-4.5 w-4.5" strokeWidth={1.75} aria-hidden="true" />
      </span>
      <div className="min-w-0 flex-1">
        <p role="status" aria-live="polite" className={`text-sm font-semibold ${isActive ? 'text-primary' : 'text-ink'}`}>
          {copy.label}
        </p>
        <p className="truncate text-xs text-muted">{copy.hint}</p>
      </div>
      <VoiceWaveform active={isActive} />
      {isActive && (
        <span className="text-sm font-semibold tabular-nums text-ink" aria-label={`Answering for ${formatSeconds(activeSeconds)}`}>
          {formatSeconds(activeSeconds)}
        </span>
      )}
    </div>
  )
}

export default VoiceStatusBar
