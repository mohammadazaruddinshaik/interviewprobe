import Button from '../../ui/Button.jsx'
import { MicIcon, SpeakerIcon, StopIcon } from '../../ui/icons.jsx'

// A compact bar exposing only existing capabilities (replay/stop, mic
// start/stop, submit) — no new interview actions. Every control here calls
// straight into the commands useVoiceInterviewSession() already exposes;
// this component holds no voice logic of its own.
function VoiceControls({
  isSpeakerSpeaking,
  speakerDisabled,
  speakerSupported,
  onReplay,
  onStopSpeaking,

  micUiState,
  micDisabled,
  micSupported,
  onStartListening,
  onStopListening,

  canSubmit,
  submitting,
  onSubmit,
}) {
  const isListening = micUiState === 'listening'
  const isProcessing = micUiState === 'processing'

  function handleSpeakerClick() {
    if (isSpeakerSpeaking) {
      onStopSpeaking()
    } else {
      onReplay()
    }
  }

  function handleMicClick() {
    if (isListening) {
      onStopListening()
    } else {
      onStartListening()
    }
  }

  return (
    <div className="border-t border-line/70 bg-white/50">
      <div className="mx-auto flex max-w-3xl flex-wrap items-center justify-center gap-3 px-6 py-4 sm:px-8">
        {speakerSupported ? (
          <button
            type="button"
            onClick={handleSpeakerClick}
            disabled={speakerDisabled}
            title={speakerDisabled ? 'Unavailable while the microphone is active' : undefined}
            aria-pressed={isSpeakerSpeaking}
            className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium transition-colors duration-200 disabled:cursor-not-allowed disabled:opacity-50 ${
              isSpeakerSpeaking
                ? 'border-accent/40 bg-accent-soft text-accent'
                : 'border-line bg-white/70 text-ink hover:border-ink/30 hover:bg-white'
            }`}
          >
            {isSpeakerSpeaking ? <StopIcon className="h-4 w-4" /> : <SpeakerIcon className="h-4 w-4" />}
            {isSpeakerSpeaking ? 'Stop' : 'Replay question'}
          </button>
        ) : (
          <p className="text-xs text-muted">Voice output isn't supported in this browser.</p>
        )}

        {micSupported ? (
          <button
            type="button"
            onClick={handleMicClick}
            disabled={micDisabled || isProcessing}
            title={micDisabled && !isProcessing ? 'Unavailable while the question is playing' : undefined}
            aria-pressed={isListening}
            aria-busy={isListening || isProcessing}
            className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium transition-colors duration-200 disabled:cursor-not-allowed disabled:opacity-50 ${
              isListening
                ? 'border-error/40 bg-error/10 text-error'
                : 'border-line bg-white/70 text-ink hover:border-ink/30 hover:bg-white'
            }`}
          >
            <MicIcon className={`h-4 w-4 ${isListening ? 'animate-pulse' : ''}`} />
            {isProcessing ? 'Processing…' : isListening ? 'Stop' : 'Speak answer'}
          </button>
        ) : (
          <p className="text-xs text-muted">Voice input isn't supported in this browser. Type your answer instead.</p>
        )}

        <Button onClick={onSubmit} disabled={!canSubmit} aria-busy={submitting} variant="primary" withArrow={!submitting}>
          {submitting ? 'Evaluating your answer…' : 'Submit answer'}
        </Button>
      </div>
    </div>
  )
}

export default VoiceControls
