import { useEffect, useRef, useState } from 'react'
import Button from '../../ui/Button.jsx'
import InterviewShell from '../room/InterviewShell.jsx'
import InterviewerVideo from '../room/InterviewerVideo.jsx'
import { createVoiceProviders } from '../../../voice/providers/index.js'
import { INTERVIEWER } from './interviewer.js'

// A brief, spoken opening — never a jump straight into a technical
// question, never a giant modal. Reuses the exact interviewer
// portrait/voice this room already has; the TTS call here is a genuinely
// one-off utterance, created and disposed entirely within this component's
// own lifetime, since the main voice session (useVoiceInterviewSession)
// doesn't start until the interview room itself mounts. "Begin" is always
// reachable immediately — nothing here ever requires waiting for speech to
// finish, and it also stops the intro speaking if pressed early.
function WelcomeIntro({ roleLabel, onBegin }) {
  const [isSpeaking, setIsSpeaking] = useState(false)
  const providersRef = useRef(null)

  useEffect(() => {
    const providers = createVoiceProviders()
    providersRef.current = providers

    // Real data only: the actual role the candidate selected. No invented
    // candidate name, no time-of-day greeting — neither is available here,
    // and guessing either would be exactly the kind of fabrication this
    // task's data-honesty rule forbids.
    const text = roleLabel
      ? `Welcome to your technical interview. We'll spend up to forty-five minutes together on the ${roleLabel} role — I'll ask a series of questions and follow up on your answers as we go. Let's begin with a brief introduction.`
      : "Welcome to your technical interview. We'll spend up to forty-five minutes together — I'll ask a series of questions and follow up on your answers as we go. Let's begin with a brief introduction."

    providers.tts.speak(text, {
      onStart: () => setIsSpeaking(true),
      onNaturalEnd: () => setIsSpeaking(false),
      onStopped: () => setIsSpeaking(false),
      onError: () => setIsSpeaking(false),
    })

    return () => {
      providers.tts.dispose()
    }
    // Deliberately runs once: this is a single spoken moment for this
    // mount, not something that should replay mid-intro.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function handleBegin() {
    providersRef.current?.tts.stop()
    onBegin()
  }

  return (
    <InterviewShell>
      <div className="flex flex-1 flex-col items-center justify-center gap-7 px-4 py-10 text-center sm:px-6">
        <InterviewerVideo interviewer={INTERVIEWER} isSpeaking={isSpeaking} />

        <div className="max-w-md">
          <p className="text-lg font-semibold leading-snug text-ink sm:text-xl">Welcome to your technical interview.</p>
          <p className="mt-3 text-sm leading-relaxed text-muted sm:text-base">
            We'll spend up to 45 minutes together{roleLabel ? ` on the ${roleLabel} role` : ''} — I'll ask a series of
            questions and follow up on your answers as we go.
          </p>
          <p className="mt-3 text-sm leading-relaxed text-muted sm:text-base">Let's begin with a brief introduction.</p>
        </div>

        <Button onClick={handleBegin} variant="primary" withArrow>
          Begin
        </Button>
      </div>
    </InterviewShell>
  )
}

export default WelcomeIntro
