import InterviewerAvatar from './InterviewerAvatar.jsx'
import InterviewerIdentity from './InterviewerIdentity.jsx'
import InterviewSubtitles from './InterviewSubtitles.jsx'
import SpeakingIndicator from './SpeakingIndicator.jsx'

// The visually dominant half of the room. Presentational only — every value
// here is handed down from VoiceInterviewView, which is the only place
// reading the session hook.
function InterviewerStage({
  interviewer,
  isSpeaking,
  questionText,
  status,
  interimTranscript,
  answer,
  onAnswerChange,
  onSubmit,
  submitting,
  headingRef,
}) {
  return (
    <section className="motion-safe:animate-rise flex flex-col items-center rounded-2xl border border-line bg-white/40 p-6 text-center sm:p-8">
      <InterviewerAvatar initials={interviewer.initials} isSpeaking={isSpeaking} />
      <div className="mt-4">
        <InterviewerIdentity name={interviewer.name} role={interviewer.role} />
      </div>
      <div className="mt-3">
        <SpeakingIndicator active={isSpeaking} />
      </div>

      <InterviewSubtitles
        interviewerName={interviewer.name}
        questionText={questionText}
        isInterviewerActive={isSpeaking}
        status={status}
        interimTranscript={interimTranscript}
        answer={answer}
        onAnswerChange={onAnswerChange}
        onSubmit={onSubmit}
        submitting={submitting}
        headingRef={headingRef}
      />
    </section>
  )
}

export default InterviewerStage
