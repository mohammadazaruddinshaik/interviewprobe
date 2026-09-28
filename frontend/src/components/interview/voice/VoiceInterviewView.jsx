import CandidateTile from '../room/CandidateTile.jsx'
import InterviewControls from '../room/InterviewControls.jsx'
import InterviewNavbar from '../room/InterviewNavbar.jsx'
import InterviewShell from '../room/InterviewShell.jsx'
import InterviewSidebar from '../room/InterviewSidebar.jsx'
import InterviewerVideo from '../room/InterviewerVideo.jsx'
import LiveTranscript from '../room/LiveTranscript.jsx'
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
  onSubmit,
  submitting,
  headingRef,
  transcript = [],
  earlierAnswersCount = 0,
  topics = [],
  currentTopic,
  onEndInterview,
  ending = false,
  submitError = null,
}) {
  const { state, activeChannel, isSpeakerSpeaking, micUiState, ttsSupported, sttSupported, commands } = voice

  const questionText = question?.text ?? ''
  const leadIn = question?.lead_in ?? ''
  const canSubmit = answer.trim().length > 0 && !submitting
  const hasError = state.status === VOICE_STATUS.ERROR && state.error
  const isCandidateTurn =
    state.status === VOICE_STATUS.CANDIDATE_LISTENING ||
    state.status === VOICE_STATUS.CANDIDATE_SPEAKING ||
    state.status === VOICE_STATUS.PROCESSING

  const answeredCount = earlierAnswersCount + transcript.length

  return (
    <InterviewShell fit>
      <InterviewNavbar onEndInterview={onEndInterview} ending={ending} endDisabled={submitting} />

      {/* Desktop (lg+): a single-screen, three-column room — session
          context | interviewer + question + voice dock | questions &
          transcript — laid out inside the viewport-tall shell. The
          interviewer frame keeps a compact 16:9 (it only shrinks when the
          viewport is genuinely short), the side panels hug their content
          instead of stretching into empty slabs, and the voice dock follows
          the question directly — one contiguous stage/question/controls
          stack, as in the reference.
          Below lg it recomposes by priority via `order-*` rather than
          shrinking the desktop grid: interviewer, question, voice status,
          Finish Answer, then questions & transcript, then session context
          (side by side on tablets, stacked on phones). */}
      <main className="grid flex-1 grid-cols-1 content-start gap-4 px-4 pb-4 pt-3 sm:px-6 sm:pb-6 md:grid-cols-2 lg:min-h-0 lg:content-stretch lg:grid-cols-[200px_minmax(0,1fr)_260px] lg:grid-rows-[minmax(0,1fr)] lg:gap-4 lg:px-6 lg:pb-5 xl:grid-cols-[minmax(0,0.84fr)_minmax(0,2fr)_minmax(0,1fr)] xl:gap-5">
        <InterviewSidebar
          roleLabel={roleLabel}
          answeredCount={answeredCount}
          topics={topics}
          currentTopic={currentTopic}
          answeredTopics={transcript.map((entry) => entry.topic)}
          className="order-3 min-w-0 md:self-start lg:order-1"
        />

        <div className="order-1 flex min-w-0 flex-col gap-3 md:col-span-2 lg:order-2 lg:col-span-1 lg:min-h-0">
          <div className="flex flex-col gap-3 lg:min-h-0 lg:shrink">
            {/* The room's compact presence row — interviewer, small and
                elegant, beside the candidate's own optional self-view.
                Neither dominates; the question below remains the room's
                actual focal point. */}
            <div className="flex items-center justify-between gap-3">
              <InterviewerVideo interviewer={interviewer} isSpeaking={isSpeakerSpeaking} />
              <CandidateTile status={state.status} />
            </div>

            {/* Sits directly under the interviewer frame. On desktop the
                frame is the flexible part of the room, so it gives up the
                banner's height and the room still fits the viewport. */}
            {(hasError || submitError) && (
              <div className="flex shrink-0 flex-col gap-2">
                {hasError && (
                  <div
                    role="alert"
                    aria-live="assertive"
                    className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 rounded-2xl border border-danger/30 bg-glass/80 px-4 py-2.5 text-sm text-danger shadow-glass-sm lg:flex-nowrap"
                  >
                    <span className="min-w-0">{state.error.message}</span>
                    {state.error.recoverable && (
                      <button type="button" onClick={commands.clearError} className="shrink-0 font-medium underline underline-offset-2">
                        Dismiss
                      </button>
                    )}
                  </div>
                )}
                {submitError && (
                  <p
                    role="alert"
                    aria-live="assertive"
                    className="rounded-2xl border border-danger/30 bg-glass/80 px-4 py-2.5 text-sm text-danger shadow-glass-sm"
                  >
                    {submitError}
                  </p>
                )}
              </div>
            )}
          </div>

          <QuestionPanel questionText={questionText} questionId={question?.id} leadIn={leadIn} headingRef={headingRef} />

          {/* Transcript-first candidate speech: appears here, directly
              above the voice dock, never underneath the question above. */}
          <LiveTranscript answer={answer} interimTranscript={state.interimTranscript} isActive={isCandidateTurn} />

          {/* The voice dock: status + controls. Stacked on smaller screens;
              one row on wide desktops so the interviewer frame keeps its
              height inside the single-screen room. */}
          <div className="flex shrink-0 flex-col gap-3 lg:flex-row lg:items-center lg:gap-4">
            <div className="min-w-0 lg:flex-1">
              <VoiceStatusBar status={state.status} />
            </div>

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
        </div>

        <TranscriptPanel
          transcript={transcript}
          currentQuestionText={questionText}
          earlierAnswersCount={earlierAnswersCount}
          className="order-2 min-w-0 md:self-start lg:order-3"
        />
      </main>
    </InterviewShell>
  )
}

export default VoiceInterviewView
