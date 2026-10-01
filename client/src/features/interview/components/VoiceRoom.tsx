import { useState } from 'react'
import { useRetryCountdown } from '../hooks/useRetryCountdown'
import type { useInterviewRoom } from '../hooks/useInterviewRoom'
import type { RoomState } from '../hooks/roomReducer'
import { useVoiceTurn } from '../hooks/useVoiceTurn'
import { useCamera } from '../voice/useCamera'
import CameraPreview from './CameraPreview'
import EndInterviewDialog from './EndInterviewDialog'
import RoomBackdrop from './RoomBackdrop'
import RoomHeader from './RoomHeader'
import InterviewPausedOverlay from './InterviewPausedOverlay'
import { useInterviewMode } from '../hooks/useInterviewMode'
import TranscriptDrawer from './TranscriptDrawer'
import VoiceStage from './VoiceStage'

type Ready = Extract<RoomState, { phase: 'ready' }>

/**
 * The live room. Mounted only while the interview is ready, so leaving it (completion, navigation) unmounts
 * the voice hooks, which stop speech playback, close the microphone/STT socket and release the camera.
 */
function VoiceRoom({ state, room }: { state: Ready; room: ReturnType<typeof useInterviewRoom> }) {
  const [transcriptOpen, setTranscriptOpen] = useState(false)
  const camera = useCamera()
  const secondsLeft = useRetryCountdown(state.turn.status === 'rateLimited' ? state.turn.until : null)

  const voice = useVoiceTurn({
    question: state.question,
    turn: state.turn,
    endFlow: state.endFlow,
    attemptAnswer: state.attempt?.answer ?? null,
    secondsLeft,
    submit: room.submit,
    discardAttempt: room.discardAttempt,
    notify: room.notify,
  })
  const mode = useInterviewMode(state.endFlow.status !== 'ending')
  const busy = state.turn.status === 'submitting' || state.endFlow.status === 'ending'

  return (
    <div className="relative min-h-[100dvh] text-cream">
      <RoomBackdrop />
      <RoomHeader
        role={state.interview.role}
        onTranscript={() => setTranscriptOpen(true)}
        onEnd={room.openEnd}
        endDisabled={busy}
        onFullscreen={mode.supported && !mode.fullscreen ? mode.enter : null}
      />
      <VoiceStage
        question={state.question}
        stage={voice.stage}
        notice={voice.notice}
        restoredAnswer={state.attempt?.answer ?? null}
        speechMeter={voice.speechMeter}
        micMeter={voice.micMeter}
        actions={voice.actions}
      />
      <CameraPreview state={camera.state} onStart={camera.start} onStop={camera.stop} />
      <TranscriptDrawer open={transcriptOpen} onClose={() => setTranscriptOpen(false)} entries={state.transcript} current={state.question} />
      {mode.paused && <InterviewPausedOverlay onReturn={mode.resume} />}
      <EndInterviewDialog flow={state.endFlow} onCancel={room.closeEnd} onConfirm={room.confirmEnd} />
    </div>
  )
}

export default VoiceRoom
