import { SpeakerIcon, StopIcon } from '../ui/icons.jsx'

// Purely presentational: all TTS lifecycle, auto-play timing, and
// cancellation-vs-natural-completion logic now lives centrally in
// useVoiceInterviewSession/voiceReducer — this component only renders the
// state it's handed and calls the two commands it's given.
function QuestionSpeaker({ text, isSpeaking, hasError, disabled, supported, onReplay, onStop }) {
  if (!supported) return null

  const isDisabled = !text || disabled

  function handleClick() {
    if (isSpeaking) {
      onStop()
    } else {
      onReplay()
    }
  }

  return (
    <span className="inline-flex flex-col items-center gap-1">
      <button
        type="button"
        onClick={handleClick}
        disabled={isDisabled}
        title={disabled ? 'Unavailable while the microphone is active' : undefined}
        aria-pressed={isSpeaking}
        aria-label={isSpeaking ? 'Stop listening to question' : 'Listen to question'}
        className={`inline-flex h-8 w-8 items-center justify-center rounded-full border transition-colors duration-200 disabled:cursor-not-allowed disabled:opacity-50 ${
          isSpeaking
            ? 'border-accent/40 bg-accent-soft text-accent'
            : hasError
              ? 'border-error/30 bg-white/70 text-ink hover:border-error/50'
              : 'border-line bg-white/70 text-ink hover:border-ink/30 hover:bg-white'
        }`}
      >
        {isSpeaking ? <StopIcon className="h-3.5 w-3.5" /> : <SpeakerIcon className="h-3.5 w-3.5" />}
      </button>

      {hasError && (
        <span role="alert" aria-live="assertive" className="text-[11px] text-error">
          Couldn't play audio
        </span>
      )}
    </span>
  )
}

export default QuestionSpeaker
