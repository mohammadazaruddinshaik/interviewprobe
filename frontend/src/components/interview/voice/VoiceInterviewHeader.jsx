import InterviewHeader from '../InterviewHeader.jsx'

// A dedicated file (rather than using InterviewHeader directly in
// VoiceInterviewView) leaves room to add room-specific header content later
// without touching the page.
function VoiceInterviewHeader({ roleLabel }) {
  return <InterviewHeader roleLabel={roleLabel} />
}

export default VoiceInterviewHeader
