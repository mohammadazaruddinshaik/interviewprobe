import { useEffect, useRef, useState } from 'react'
import { MicIcon } from '../ui/icons.jsx'

const SUCCESS_DISPLAY_MS = 1800

const LABELS = {
  idle: 'Speak answer',
  listening: 'Listening…',
  processing: 'Processing…',
  success: 'Added to answer',
}

// Purely presentational: all STT lifecycle now lives centrally in
// useVoiceInterviewSession/voiceReducer — this component only renders the
// state it's handed and calls the two commands it's given. The one thing it
// still owns locally is the brief "Added to answer" success glow: cosmetic
// display timing, not voice logic, so it has no place in the shared
// reducer. `lastTranscriptSeq` changing is what triggers it — keyed by a
// monotonic delivery sequence (not by transcript text) so a legitimately
// repeated phrase, or a second chunk within the same listening attempt,
// still re-triggers the glow.
function VoiceInputButton({ micState, error, disabled, lockedBySpeaker, supported, lastTranscriptSeq, onStart, onStop }) {
  const [showSuccess, setShowSuccess] = useState(false)
  const seenSeqRef = useRef(lastTranscriptSeq)

  useEffect(() => {
    if (!lastTranscriptSeq || lastTranscriptSeq === seenSeqRef.current) return
    seenSeqRef.current = lastTranscriptSeq
    setShowSuccess(true)
    const timeoutId = setTimeout(() => setShowSuccess(false), SUCCESS_DISPLAY_MS)
    return () => clearTimeout(timeoutId)
  }, [lastTranscriptSeq])

  if (!supported) {
    return (
      <p className="text-xs text-muted">
        Voice input isn't supported in this browser. Try Chrome or Edge, or type your answer.
      </p>
    )
  }

  const isListening = micState === 'listening'
  const isProcessing = micState === 'processing'
  const hasError = micState === 'error'
  const displayState = showSuccess ? 'success' : micState

  function handleClick() {
    if (isListening) {
      onStop()
    } else {
      onStart()
    }
  }

  return (
    <div className="flex flex-col items-start gap-1.5">
      <button
        type="button"
        onClick={handleClick}
        disabled={disabled || isProcessing}
        title={lockedBySpeaker ? 'Unavailable while the question is playing' : undefined}
        aria-pressed={isListening}
        aria-busy={isListening || isProcessing}
        className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium transition-colors duration-200 disabled:cursor-not-allowed disabled:opacity-50 ${
          isListening
            ? 'border-error/40 bg-error/10 text-error'
            : hasError
              ? 'border-error/30 bg-white/70 text-ink hover:border-error/50'
              : 'border-line bg-white/70 text-ink hover:border-ink/30 hover:bg-white'
        }`}
      >
        <MicIcon className={`h-4 w-4 ${isListening ? 'animate-pulse' : ''}`} />
        {LABELS[displayState] ?? LABELS.idle}
      </button>

      {hasError && error && (
        <p role="alert" aria-live="assertive" className="text-xs text-error">
          {error}
        </p>
      )}
    </div>
  )
}

export default VoiceInputButton
