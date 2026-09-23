import { createRemoteSttProvider } from './remoteSttProvider.js'
import { createRemoteTtsProvider } from './remoteTtsProvider.js'

// The one place that knows which concrete providers exist. The voice
// session only ever calls this factory and gets back { tts, stt } shaped to
// ttsProvider.js/sttProvider.js — it never sees a provider name or which
// implementation backs it.
//
// InterviewProbe is voice-first via Deepgram (STT) and Azure Speech (TTS)
// only — there is no browser Web Speech API implementation to fall back to,
// deliberately: silently degrading to a different, unmonitored speech
// engine would mask a real production misconfiguration. `VITE_TTS_MODE`/
// `VITE_STT_MODE` are plain application-level switches (never a
// credential — remoteTtsProvider.js and remoteSttProvider.js only ever
// talk to this app's own backend, which holds the actual Azure Speech /
// Deepgram credentials) whose only supported value is `"remote"`; anything
// else — unset, mistyped, or a mode that used to select a browser
// implementation — fails fast and loud rather than silently choosing
// something else.
function createTtsProvider() {
  const mode = import.meta.env.VITE_TTS_MODE
  if (mode !== 'remote') {
    throw new Error(
      `Unsupported VITE_TTS_MODE "${mode}". Voice output only supports "remote" (Azure Speech via this app's backend) — set VITE_TTS_MODE=remote.`,
    )
  }
  return createRemoteTtsProvider()
}

function createSttProvider() {
  const mode = import.meta.env.VITE_STT_MODE
  if (mode !== 'remote') {
    throw new Error(
      `Unsupported VITE_STT_MODE "${mode}". Voice input only supports "remote" (Deepgram via this app's backend) — set VITE_STT_MODE=remote.`,
    )
  }
  return createRemoteSttProvider()
}

export function createVoiceProviders() {
  return {
    tts: createTtsProvider(),
    stt: createSttProvider(),
  }
}
