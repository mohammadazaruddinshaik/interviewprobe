import { createVoiceError } from '../errors.js'

// speechSynthesis is a single global, browser-wide resource — undefined
// entirely in some environments, so every call site feature-detects via
// `isSupported` before touching it.
function detectSupport() {
  return typeof window !== 'undefined' && 'speechSynthesis' in window && typeof window.SpeechSynthesisUtterance === 'function'
}

// `getVoices()` can return [] until the async `voiceschanged` event fires;
// when that happens this simply falls through to the browser's own default
// voice.
function pickEnglishVoice() {
  const voices = window.speechSynthesis.getVoices()
  return voices.find((voice) => voice.lang === 'en-US') ?? voices.find((voice) => voice.lang.startsWith('en')) ?? null
}

// The browser SpeechSynthesis implementation of the TtsProvider contract
// (ttsProvider.js). A plain factory, not a React hook — a provider must be
// callable from outside component render (the session hook creates one
// instance and keeps it for the life of the interview), and swappable for a
// remote implementation satisfying the exact same shape.
export function createBrowserTtsProvider() {
  const isSupported = detectSupport()
  let currentUtterance = null

  function stop() {
    if (!isSupported) return
    // Cancelling fires the in-flight utterance's own `onerror`
    // ('canceled'/'interrupted') — handled below as onStopped, never as
    // onNaturalEnd.
    window.speechSynthesis.cancel()
  }

  function speak(text, { onStart, onNaturalEnd, onStopped, onError } = {}) {
    if (!isSupported) {
      onError?.(createVoiceError('unsupported', 'Voice output is not supported in this browser.', { recoverable: false }))
      return
    }
    if (!text) return

    // Cancel anything already in flight so at most one utterance is ever
    // active, and so a second speak() call can never overlap the first.
    window.speechSynthesis.cancel()

    const utterance = new window.SpeechSynthesisUtterance(text)
    const voice = pickEnglishVoice()
    if (voice) {
      utterance.voice = voice
      utterance.lang = voice.lang
    }

    // Each handler checks it's still the current utterance before firing a
    // callback, so a stale event from an utterance speak() just superseded
    // can never be mistaken for the one that replaced it.
    utterance.onstart = () => {
      if (currentUtterance === utterance) onStart?.()
    }
    utterance.onend = () => {
      if (currentUtterance === utterance) onNaturalEnd?.()
    }
    utterance.onerror = (event) => {
      if (currentUtterance !== utterance) return
      if (event.error === 'canceled' || event.error === 'interrupted') {
        onStopped?.()
        return
      }
      onError?.(createVoiceError(event.error ?? 'unknown', 'Voice playback failed. Please try again.'))
    }

    currentUtterance = utterance
    window.speechSynthesis.speak(utterance)
  }

  function dispose() {
    stop()
    currentUtterance = null
  }

  return { isSupported, speak, stop, dispose }
}
