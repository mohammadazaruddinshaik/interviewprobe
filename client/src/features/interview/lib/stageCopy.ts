import type { Stage } from '../hooks/useVoiceTurn'

/** The single status line under the presence (text, so state never relies on animation alone). */
export function stageText(stage: Stage): string {
  switch (stage.kind) {
    case 'speechLoading': return 'Preparing'
    case 'aiSpeaking': return 'Speaking'
    case 'needsTap': return 'Ready when you are'
    case 'ready': return 'Your turn'
    case 'connecting': return 'Opening your microphone'
    case 'listening': return 'Your turn'
    case 'candidateSpeaking': return 'You’re speaking'
    case 'finishing': return 'Sending your answer'
    case 'thinking': return 'Thinking'
    case 'completing': return 'Wrapping up'
    case 'micProblem': return 'Microphone needs attention'
    case 'speechFailed': return 'Audio unavailable'
    case 'retry': return 'Let’s try that again'
  }
}
