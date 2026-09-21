import { createVoiceError } from '../errors.js'

function detectRecognitionCtor() {
  return typeof window !== 'undefined' ? window.SpeechRecognition || window.webkitSpeechRecognition : undefined
}

// Maps SpeechRecognitionErrorEvent.error codes to candidate-facing copy.
// `aborted` fires whenever `.stop()` is called (including our own,
// intentional stop) — never surfaced as a failure.
const ERROR_MESSAGES = {
  'not-allowed': 'Microphone access was denied. Allow microphone access in your browser to use voice input.',
  'service-not-allowed': 'Microphone access was denied. Allow microphone access in your browser to use voice input.',
  'no-speech': "We didn't catch that — try speaking again.",
  'audio-capture': 'No microphone was found. Check your device and try again.',
  network: 'A network error interrupted voice recognition. Please try again.',
}

// The browser SpeechRecognition implementation of the SttProvider contract
// (sttProvider.js). A plain factory, not a React hook — see
// browserTtsProvider.js for why. Note: `interimResults` stays `false` here,
// preserving the exact current behavior (final transcripts only) — turning
// it on is a real, user-visible change this task deliberately does not make;
// see the contract's onInterim doc for how a future provider would use it.
export function createBrowserSttProvider() {
  const RecognitionCtor = detectRecognitionCtor()
  const isSupported = Boolean(RecognitionCtor)
  let activeRecognition = null

  function stop() {
    activeRecognition?.stop()
  }

  // `onInterim` is part of the SttProvider contract (sttProvider.js) but
  // deliberately not accepted here: `interimResults` stays `false` below, so
  // this implementation never has interim text to report. A provider that
  // can supply it would add it to this destructure.
  function start({ onStart, onSpeechDetected, onSpeechEnd, onFinal, onStopped, onError } = {}) {
    if (!isSupported) {
      onError?.(
        createVoiceError('unsupported', 'Voice input is not supported in this browser. Try Chrome or Edge, or type your answer.', {
          recoverable: false,
        }),
      )
      return
    }
    if (activeRecognition) return // a second attempt must never overlap a still-active one

    const recognition = new RecognitionCtor()
    recognition.lang = 'en-US'
    recognition.interimResults = false
    recognition.maxAlternatives = 1

    // Tracks whether onresult or onerror already produced a terminal
    // outcome, so onend's fallback below only fires for the genuinely
    // unusual case of ending with neither (defends the same edge case the
    // pre-provider hook defended against).
    let settled = false

    recognition.onstart = () => onStart?.()
    recognition.onspeechstart = () => onSpeechDetected?.()
    recognition.onspeechend = () => onSpeechEnd?.()

    recognition.onresult = (event) => {
      settled = true
      const transcript = Array.from(event.results)
        .map((result) => result[0]?.transcript ?? '')
        .join(' ')
        .trim()
      if (transcript) onFinal?.(transcript)
      // Web Speech API's non-continuous recognition always ends right after
      // one result, whether or not it produced text — this is what tells
      // the caller the listening attempt itself is over, distinct from
      // whether a transcript arrived (see sttProvider.js's onStopped doc).
      onStopped?.()
    }

    recognition.onerror = (event) => {
      settled = true
      if (event.error === 'aborted') {
        onStopped?.()
        return
      }
      onError?.(createVoiceError(event.error ?? 'unknown', ERROR_MESSAGES[event.error] ?? 'Voice input failed. Please try again or type your answer.'))
    }

    recognition.onend = () => {
      activeRecognition = null
      if (!settled) onStopped?.()
    }

    activeRecognition = recognition
    recognition.start()
  }

  function dispose() {
    stop()
    activeRecognition = null
  }

  return { isSupported, start, stop, dispose }
}
