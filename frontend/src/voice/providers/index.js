import { createBrowserSttProvider } from './browserSttProvider.js'
import { createBrowserTtsProvider } from './browserTtsProvider.js'
import { createRemoteSttProvider } from './remoteSttProvider.js'
import { createRemoteTtsProvider } from './remoteTtsProvider.js'

// The one place that knows which concrete providers exist. The voice
// session only ever calls this factory and gets back { tts, stt } shaped to
// ttsProvider.js/sttProvider.js — it never sees a provider name or which
// implementation backs it.
//
// `VITE_TTS_MODE`/`VITE_STT_MODE` are plain application-level switches,
// never anything vendor-specific: "browser" (the default, and used
// whenever the value is unset or unrecognized) or "remote". No credential
// of any kind belongs in a VITE_* variable — remoteTtsProvider.js and
// remoteSttProvider.js only ever talk to this app's own backend, which
// holds the actual Azure Speech / Deepgram credentials.
function createTtsProvider() {
  const mode = import.meta.env.VITE_TTS_MODE
  if (mode === 'remote') return createRemoteTtsProvider()
  return createBrowserTtsProvider()
}

function createSttProvider() {
  const mode = import.meta.env.VITE_STT_MODE
  if (mode === 'remote') return createRemoteSttProvider()
  return createBrowserSttProvider()
}

export function createVoiceProviders() {
  return {
    tts: createTtsProvider(),
    stt: createSttProvider(),
  }
}
