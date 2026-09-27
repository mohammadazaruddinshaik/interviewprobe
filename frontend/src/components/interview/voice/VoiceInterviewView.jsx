import InterviewControls from '../room/InterviewControls.jsx'
import InterviewNavbar from '../room/InterviewNavbar.jsx'
import InterviewShell from '../room/InterviewShell.jsx'
import InterviewSidebar from '../room/InterviewSidebar.jsx'
import InterviewerVideo from '../room/InterviewerVideo.jsx'
import QuestionPanel from '../room/QuestionPanel.jsx'
import TranscriptPanel from '../room/TranscriptPanel.jsx'
import VoiceStatusBar from '../room/VoiceStatusBar.jsx'
import { VOICE_STATUS } from '../../../voice/voiceState.js'
import { INTERVIEWER } from './interviewer.js'

// The dedicated voice room. A pure presentation layer over
// useVoiceInterviewSession()'s return value (`voice`) — every child here
// just renders a slice of that same state and calls its commands; nothing
// in this tree owns TTS/STT lifecycle, talks to a speech provider
// directly, or keeps a second copy of the answer. `transcript` is the one
// piece of state this page (Interview.jsx) does own beyond the session
// hook — a same-session record of turns that have really happened.
function VoiceInterviewView({
  voice,
  interviewer = INTERVIEWER,
  question,
  roleLabel,
  answer,
  onAnswerChange,
  onSubmit,
  submitting,
  headingRef,
  transcript = [],
}) {
  const { state, activeChannel, isSpeakerSpeaking, micUiState, ttsSupported, sttSupported, commands } = voice

  const questionText = question?.text ?? ''
  const leadIn = question?.lead_in ?? ''
  const canSubmit = answer.trim().length > 0 && !submitting
  const hasError = state.status === VOICE_STATUS.ERROR && state.error

  return (
    <InterviewShell>
      <InterviewNavbar />

      {/* Mobile recomposes this into a priority-ordered single column
          (navbar, interviewer, question, voice state, Finish Answer,
          transcript) rather than shrinking the desktop 3-column dashboard
          — the sidebar's role/guidance content is real but lower priority,
          so it moves to the very end via `order-*` instead of appearing
          first just because it's the first grid column on desktop. */}
      <main className="grid grid-cols-1 flex-1 gap-4 px-4 pb-4 pt-3 sm:px-6 sm:pb-6 lg:grid-cols-[220px_minmax(0,1fr)_300px] lg:gap-5 lg:px-8 lg:pb-6 xl:grid-cols-[240px_minmax(0,1fr)_340px]">
        <InterviewSidebar roleLabel={roleLabel} className="order-3 min-w-0 lg:order-1" />

        <div className="order-1 flex min-w-0 flex-col gap-4 lg:order-2">
          <InterviewerVideo interviewer={interviewer} isSpeaking={isSpeakerSpeaking} status={state.status} />

          {hasError && (
            <div
              role="alert"
              aria-live="assertive"
              className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-danger/30 bg-glass/70 px-4 py-3 text-sm text-danger"
            >
              <span>{state.error.message}</span>
              {state.error.recoverable && (
                <button type="button" onClick={commands.clearError} className="font-medium underline underline-offset-2">
                  Dismiss
                </button>
              )}
            </div>
          )}

          <QuestionPanel
            questionText={questionText}
            leadIn={leadIn}
            interimTranscript={state.interimTranscript}
            answer={answer}
            onAnswerChange={onAnswerChange}
            onSubmit={onSubmit}
            submitting={submitting}
            headingRef={headingRef}
          />

          <VoiceStatusBar status={state.status} />

          <InterviewControls
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
          />
        </div>

        <TranscriptPanel
          transcript={transcript}
          currentQuestionText={questionText}
          currentAnswer={answer}
          interimTranscript={state.interimTranscript}
          className="order-2 min-w-0 lg:order-3"
        />
      </main>
    </InterviewShell>
  )
}

export default VoiceInterviewView
