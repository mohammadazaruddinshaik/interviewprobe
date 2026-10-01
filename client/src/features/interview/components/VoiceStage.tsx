import { Mic, RotateCcw, Volume2 } from 'lucide-react'
import type { Stage } from '../hooks/useVoiceTurn'
import { stageText } from '../lib/stageCopy'
import type { LevelMeter } from '../voice/audioLevel'
import Waveform from '../voice/Waveform'
import { useQuestionTransition } from '../hooks/useQuestionTransition'
import type { Question } from '../types/interview'
import AiPresence, { type PresenceMode } from './AiPresence'

interface VoiceStageProps {
  question: Question
  stage: Stage
  notice: string | null
  restoredAnswer: string | null
  speechMeter: () => LevelMeter | null
  micMeter: () => LevelMeter | null
  actions: {
    finishAnswer: () => void
    replay: () => void
    retrySend: () => void
    answerAgain: () => void
    speakNow: () => void
    startMic: () => void
  }
}

const MIC_PROBLEMS = {
  permission: 'Microphone access is blocked. Allow the microphone in your browser’s site settings, then try again.',
  noDevice: 'We couldn’t find a microphone. Connect one, then try again.',
  unsupported: 'This browser can’t record audio for the interview. Try the latest Chrome, Edge, Safari or Firefox.',
  unavailable: 'Voice input isn’t available right now. Please try again in a moment.',
  connection: 'We lost the connection to voice input. Please try again.',
} as const

function presenceFor(stage: Stage): PresenceMode {
  switch (stage.kind) {
    case 'speechLoading': case 'connecting': return 'preparing'
    case 'aiSpeaking': return 'speaking'
    case 'ready': case 'listening': return 'listening'
    case 'candidateSpeaking': return 'candidate'
    case 'finishing': return 'finishing'
    case 'thinking': return 'thinking'
    case 'completing': return 'completing'
    case 'needsTap': return 'preparing'
    case 'micProblem': case 'speechFailed': case 'retry': return 'error'
  }
}

const primary =
  'inline-flex h-[58px] min-w-[220px] items-center justify-center gap-2.5 rounded-2xl bg-yellow px-10 text-[17px] font-semibold text-forest shadow-[0_14px_36px_-14px_rgb(253_228_90/0.55)] outline-offset-4 transition-[background-color,translate,box-shadow] duration-200 hover:enabled:-translate-y-0.5 hover:enabled:bg-[#ffec85] focus-visible:outline-[3px] focus-visible:outline-cream disabled:cursor-not-allowed disabled:bg-cream/12 disabled:text-cream/35 disabled:shadow-none motion-reduce:transition-none motion-reduce:hover:translate-y-0'
const secondary =
  'inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-cream/25 bg-transparent px-5 text-[14px] font-semibold text-cream outline-offset-2 transition-colors hover:enabled:bg-cream/10 focus-visible:outline-[3px] focus-visible:outline-yellow disabled:opacity-50 motion-reduce:transition-none'
const quiet =
  'inline-flex min-h-11 items-center gap-2 rounded-lg px-3 text-[13px] font-medium text-cream/50 outline-offset-2 transition-colors hover:text-cream focus-visible:outline-[3px] focus-visible:outline-yellow disabled:opacity-35 motion-reduce:transition-none'

const questionType =
  'text-balance font-serif text-[23px] font-normal leading-[1.28] tracking-[-0.005em] text-cream sm:text-[30px] lg:text-[36px] [@media(max-height:700px)]:text-[22px] [@media(max-height:700px)]:sm:text-[26px] [@media(max-height:700px)]:lg:text-[28px]'

function VoiceStage({ question, stage, notice, restoredAnswer, speechMeter, micMeter, actions }: VoiceStageProps) {
  const speaking = stage.kind === 'aiSpeaking'
  const mic = stage.kind === 'listening' || stage.kind === 'candidateSpeaking'
  const canReplay = ['aiSpeaking', 'needsTap', 'ready', 'listening', 'speechFailed'].includes(stage.kind)
  const leaving = useQuestionTransition(question.id, question.text)

  // The question stays, but yields to whoever has the floor: quieter while you speak, quietest while it thinks.
  const questionTone =
    stage.kind === 'candidateSpeaking' ? 'opacity-70' : ['thinking', 'finishing', 'completing'].includes(stage.kind) ? 'opacity-45' : 'opacity-100'

  return (
    <main className="relative z-10 mx-auto flex max-w-[820px] flex-col items-center px-5 pb-[200px] pt-3 text-center [@media(max-height:720px)]:pt-0 sm:px-8 lg:pb-[150px] [@media(max-height:720px)]:pb-[120px]">
      <div data-room="presence" className="flex flex-col items-center">
        <p className="mb-1.5 text-[11px] font-semibold tracking-[0.2em] text-cream/45 [@media(max-height:720px)]:mb-0.5">AI INTERVIEWER</p>
        <AiPresence mode={presenceFor(stage)} meter={speaking ? speechMeter : micMeter} />
        {/* Whose turn it is, always in words: motion only supports it. */}
        <div role="status" aria-live="polite" className="mt-2 min-h-[30px] font-display text-[21px] font-extrabold tracking-[-0.02em] text-cream sm:text-[25px]">
          {stageText(stage)}
        </div>
      </div>

      <h1 className="sr-only">Voice interview in progress</h1>
      <section data-room="question" aria-label="Current question" className="relative mt-2 min-h-[6.5rem] w-full lg:mt-4 [@media(max-height:720px)]:mt-1">
        {leaving && (
          <div aria-hidden="true" className="ip-motion pointer-events-none absolute inset-x-0 top-0 animate-[ip-leave_0.55s_ease-in_forwards]">
            <p className={questionType}>{leaving.text}</p>
          </div>
        )}
        <div key={question.id} className={`ip-motion animate-[ip-enter_0.9s_ease-out_0.35s_both] transition-opacity duration-700 motion-reduce:transition-none ${questionTone}`}>
          {question.lead_in && <p className="mx-auto mb-3 max-w-[560px] font-serif text-[15px] italic leading-[1.5] text-cream/55">{question.lead_in}</p>}
          <p id="room-question" className={questionType}>
            {question.text}
          </p>
        </div>
      </section>

      <div className="mt-3 [@media(max-height:720px)]:mt-1">
        <Waveform meter={speaking ? speechMeter : micMeter} active={speaking || mic} tone={mic ? 'you' : 'ai'} />
      </div>

      <div className="mt-1">
        <button type="button" onClick={actions.replay} disabled={!canReplay} className={quiet} aria-label="Replay the question">
          <Volume2 size={15} aria-hidden="true" /> Replay question
        </button>
      </div>

      {stage.kind === 'speechFailed' && <p className="mt-2 max-w-[460px] text-[14px] text-cream/65">{stage.message} You can read the question above and answer when you’re ready.</p>}
      {stage.kind === 'micProblem' && <p role="alert" className="mt-2 max-w-[480px] text-[14px] text-cream/85">{MIC_PROBLEMS[stage.problem]}</p>}
      {notice && <p role="alert" className="mt-2 max-w-[480px] text-[14px] text-cream/85">{notice}</p>}
      {stage.kind === 'retry' && <p role="alert" className="mt-2 max-w-[520px] text-[14.5px] text-cream/85">{stage.message}</p>}

      <div
        data-room="controls"
        className="fixed inset-x-0 bottom-0 z-10 flex flex-col items-center gap-2 bg-gradient-to-t from-[#06110a] via-[#06110a]/85 to-transparent px-4 pb-[calc(16px+env(safe-area-inset-bottom))] pt-8"
      >
        {stage.kind === 'needsTap' && (
          <button type="button" onClick={actions.speakNow} className={primary}>
            <Volume2 size={18} aria-hidden="true" /> Hear the question
          </button>
        )}
        {stage.kind === 'speechFailed' && (
          <div className="flex flex-wrap justify-center gap-2">
            <button type="button" onClick={actions.speakNow} className={secondary}>Try audio again</button>
            <button type="button" onClick={actions.startMic} className={primary}><Mic size={18} aria-hidden="true" /> Answer now</button>
          </div>
        )}
        {stage.kind === 'ready' && (
          <button type="button" onClick={actions.startMic} className={primary}><Mic size={18} aria-hidden="true" /> Start answering</button>
        )}
        {stage.kind === 'micProblem' && (
          <button type="button" onClick={actions.startMic} className={primary}><RotateCcw size={18} aria-hidden="true" /> Try microphone again</button>
        )}
        {(stage.kind === 'listening' || stage.kind === 'candidateSpeaking') && (
          <button type="button" onClick={actions.finishAnswer} disabled={stage.kind === 'listening'} className={primary}>
            Finish answer
          </button>
        )}
        {stage.kind === 'retry' && (
          <div className="flex flex-wrap justify-center gap-2">
            {restoredAnswer ? (
              <>
                <button type="button" onClick={actions.retrySend} disabled={stage.secondsLeft > 0} className={primary}>
                  {stage.secondsLeft > 0 ? `Try again in ${stage.secondsLeft}s` : stage.restored ? 'Send my answer' : 'Try sending again'}
                </button>
                <button type="button" onClick={actions.answerAgain} className={secondary}>Answer again</button>
              </>
            ) : (
              <button type="button" onClick={actions.startMic} className={primary}>Continue</button>
            )}
          </div>
        )}
        {(stage.kind === 'listening' || stage.kind === 'candidateSpeaking') && (
          <p className="text-[12.5px] text-cream/45 [@media(max-height:720px)]:hidden">Your answer is only sent when you press Finish.</p>
        )}
      </div>
    </main>
  )
}

export default VoiceStage
