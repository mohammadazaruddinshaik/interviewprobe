import InterviewHeader from '../InterviewHeader.jsx'

// Reuses the exact same header as text mode — same role/difficulty/topic
// and question-progress display, so the two modes never visually disagree
// about where the candidate is in the interview. A dedicated file (rather
// than using InterviewHeader directly in VoiceInterviewView) leaves room to
// add room-specific header content later without touching the page.
function VoiceInterviewHeader({ roleLabel, difficultyLabel, topicLabel, questionNumber, questionLimit }) {
  return (
    <InterviewHeader
      roleLabel={roleLabel}
      difficultyLabel={difficultyLabel}
      topicLabel={topicLabel}
      questionNumber={questionNumber}
      questionLimit={questionLimit}
    />
  )
}

export default VoiceInterviewHeader
