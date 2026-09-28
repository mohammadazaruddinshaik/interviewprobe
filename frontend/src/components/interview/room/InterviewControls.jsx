import { MicIcon, SpeakerIcon, StopIcon } from '../../ui/icons.jsx'

// A compact, meeting-style control row (no card around it). Exposes exactly the
// existing capabilities (replay/stop the question, start/stop the mic,
// Finish Answer) through the exact same commands useVoiceInterviewSession()
// already provides — no new interview action, no camera/more control that
// doesn't back a real feature. "Finish Answer" is deliberately the only
// way an answer is ever submitted (see Interview.jsx's handleFinishAnswer)
// — this component never submits on its own.
function ControlButton({ active, tone = 'neutral', primary = false, label, icon, disabled, title, ariaPressed, ariaBusy, onClick }) {
  const toneClasses =
    tone === 'danger'
      ? 'border-danger/30 bg-danger text-white hover:bg-danger/90'
      : active
        ? 'border-primary/40 bg-primary-light text-primary'
        : 'border-line bg-glass/70 text-ink hover:border-primary/25 hover:bg-glass'

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={title}
      aria-pressed={ariaPressed}
      aria-busy={ariaBusy}
      className="flex flex-col items-center gap-1.5 disabled:cursor-not-allowed disabled:opacity-50"
    >
      <span
        className={`flex items-center justify-center rounded-full border transition-colors duration-200 ${
          primary ? 'h-14 w-14 shadow-glass' : 'h-11 w-11 shadow-glass-sm'
        } ${toneClasses}`}
      >
        {icon}
      </span>
      <span
        className={`max-w-[5.5rem] text-center text-xs leading-tight sm:max-w-[6.5rem] lg:max-w-none lg:whitespace-nowrap lg:text-[11px] xl:text-xs ${primary ? 'font-semibold text-ink' : 'font-medium text-muted'}`}
      >
        {label}
      </span>
    </button>
  )
}

function InterviewControls({
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
    <div className="flex shrink-0 flex-wrap items-end justify-center gap-5 sm:gap-10 lg:gap-3 xl:gap-4">
      {speakerSupported ? (
        <ControlButton
          onClick={handleSpeakerClick}
          disabled={speakerDisabled}
          title={speakerDisabled ? 'Unavailable while the microphone is active' : undefined}
          ariaPressed={isSpeakerSpeaking}
          active={isSpeakerSpeaking}
          label={isSpeakerSpeaking ? 'Stop' : 'Replay question'}
          icon={
            isSpeakerSpeaking ? <StopIcon className="h-4.5 w-4.5" /> : <SpeakerIcon className="h-4.5 w-4.5" />
          }
        />
      ) : (
        <p className="max-w-[8rem] self-center text-center text-xs text-muted">
          Voice output isn't supported in this browser.
        </p>
      )}

      <ControlButton
        onClick={onSubmit}
        disabled={!canSubmit}
        ariaBusy={submitting}
        tone="danger"
        primary
        label={submitting ? 'Evaluating your answer…' : 'Finish Answer'}
        icon={<StopIcon className="h-4.5 w-4.5" />}
      />

      {micSupported ? (
        <ControlButton
          onClick={handleMicClick}
          disabled={micDisabled || isProcessing}
          title={micDisabled && !isProcessing ? 'Unavailable while the question is playing' : undefined}
          ariaPressed={isListening}
          ariaBusy={isListening || isProcessing}
          active={isListening}
          label={isProcessing ? 'Processing…' : isListening ? 'Stop' : 'Speak answer'}
          icon={<MicIcon className={`h-4.5 w-4.5 ${isListening ? 'animate-pulse' : ''}`} />}
        />
      ) : (
        <p className="max-w-[8rem] self-center text-center text-xs text-muted">
          Voice input isn't supported here. Type your answer instead.
        </p>
      )}
    </div>
  )
}

export default InterviewControls
