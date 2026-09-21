import { VOICE_STATUS } from '../../../voice/voiceState.js'
import CandidateStage from './CandidateStage.jsx'
import { INTERVIEWER } from './interviewer.js'
import InterviewerStage from './InterviewerStage.jsx'
import VoiceControls from './VoiceControls.jsx'
import VoiceInterviewHeader from './VoiceInterviewHeader.jsx'

// The dedicated voice room. A pure presentation layer over
// useVoiceInterviewSession()'s return value (`voice`) — every child here
// just renders a slice of that same state and calls its commands; nothing
// in this tree owns TTS/STT lifecycle, calls SpeechSynthesis/
// SpeechRecognition directly, or keeps a second copy of the answer.
function VoiceInterviewView({
  voice,
  interviewer = INTERVIEWER,
  question,
  questionLimit,
  roleLabel,
  difficultyLabel,
  topicLabel,
  answer,
  onAnswerChange,
  onSubmit,
  submitting,
  headingRef,
}) {
  const { state, activeChannel, isSpeakerSpeaking, micUiState, ttsSupported, sttSupported, commands } = voice

  const questionText = question?.text ?? ''
  const canSubmit = answer.trim().length > 0 && !submitting
  const hasError = state.status === VOICE_STATUS.ERROR && state.error

  return (
    <div className="flex min-h-screen flex-col bg-cream">
      <VoiceInterviewHeader
        roleLabel={roleLabel}
        difficultyLabel={difficultyLabel}
        topicLabel={topicLabel}
        questionNumber={question?.sequence}
        questionLimit={questionLimit}
      />

      <main className="mx-auto grid w-full max-w-5xl flex-1 gap-4 px-6 py-6 sm:px-8 lg:grid-cols-[1fr_260px] lg:items-start lg:gap-6">
        <InterviewerStage
          interviewer={interviewer}
          isSpeaking={isSpeakerSpeaking}
          questionText={questionText}
          status={state.status}
          interimTranscript={state.interimTranscript}
          answer={answer}
          onAnswerChange={onAnswerChange}
          onSubmit={onSubmit}
          submitting={submitting}
          headingRef={headingRef}
        />

        <CandidateStage status={state.status} />
      </main>

      {hasError && (
        <div className="mx-auto w-full max-w-3xl px-6 pb-2 sm:px-8">
          <div
            role="alert"
            aria-live="assertive"
            className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-error/30 bg-white/70 px-4 py-3 text-sm text-error"
          >
            <span>{state.error.message}</span>
            {state.error.recoverable && (
              <button type="button" onClick={commands.clearError} className="font-medium underline underline-offset-2">
                Dismiss
              </button>
            )}
          </div>
        </div>
      )}

      <VoiceControls
        isSpeakerSpeaking={isSpeakerSpeaking}
        speakerDisabled={activeChannel === 'mic' || !questionText}
        speakerSupported={ttsSupported}
        onReplay={commands.replayQuestion}
        onStopSpeaking={commands.stopSpeaking}
        micUiState={micUiState}
        micDisabled={submitting || activeChannel === 'speaker'}
        micSupported={sttSupported}
        onStartListening={commands.startListening}
        onStopListening={commands.stopListening}
        canSubmit={canSubmit}
        submitting={submitting}
        onSubmit={onSubmit}
        onExitVoiceMode={commands.disableVoiceMode}
      />
    </div>
  )
}

export default VoiceInterviewView
