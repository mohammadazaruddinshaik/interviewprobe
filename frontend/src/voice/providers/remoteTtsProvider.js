import { createVoiceError } from '../errors.js'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

// fetch + Audio + AbortController are all that's required; every real
// target environment (any modern browser) has all three, so this is a
// deliberately simple check rather than feature-testing each API.
function detectSupport() {
  return (
    typeof window !== 'undefined' &&
    typeof window.Audio === 'function' &&
    typeof fetch === 'function' &&
    typeof AbortController === 'function'
  )
}

// The Azure-backed implementation of the TtsProvider contract
// (ttsProvider.js) — this module is the ONLY place that knows synthesis
// happens on the backend; everything it returns is indistinguishable from
// browserTtsProvider.js to any caller. No Azure credential or Azure-specific
// identifier ever appears here or crosses the network from this side: the
// request carries only { text, voice: "default" }.
export function createRemoteTtsProvider() {
  const isSupported = detectSupport()

  // At most one attempt (fetch + eventual Audio playback) is ever "current".
  // Every async continuation (the fetch resolving, the body finishing, a
  // playback event) checks `current === entry` before doing anything
  // observable, so a superseded or stopped attempt's late-arriving work is
  // always inert — the same identity-guard shape browserTtsProvider.js uses
  // for utterances, just spanning a network request instead of a single
  // synchronous call.
  let current = null

  function teardown(entry) {
    if (entry.audio) {
      entry.audio.onplay = null
      entry.audio.onended = null
      entry.audio.onerror = null
      entry.audio.pause()
    }
    if (entry.objectUrl) URL.revokeObjectURL(entry.objectUrl)
    entry.controller.abort()
  }

  // Ends whatever attempt is currently active, if any, firing its
  // onStopped exactly once. Used by both stop() and a superseding speak()
  // call, so "something else took over" looks identical to the caller that
  // got cut off either way — never onNaturalEnd, never onError.
  function endCurrent() {
    if (!current) return
    const entry = current
    current = null
    teardown(entry)
    entry.callbacks.onStopped?.()
  }

  function stop() {
    if (!isSupported) return
    endCurrent()
  }

  function speak(text, callbacks = {}) {
    if (!isSupported) {
      callbacks.onError?.(
        createVoiceError('unsupported', 'Voice output is not supported in this browser.', { recoverable: false }),
      )
      return
    }
    if (!text) return

    endCurrent()

    const controller = new AbortController()
    const entry = { audio: null, objectUrl: null, controller, callbacks }
    current = entry

    fetch(`${API_BASE_URL}/voice/tts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, voice: 'default' }),
      signal: controller.signal,
    })
      .then(async (response) => {
        if (current !== entry) return // stopped/superseded while the request was in flight

        if (!response.ok) {
          current = null
          teardown(entry)
          callbacks.onError?.(
            createVoiceError('service-error', 'Voice output could not be generated. Please try again.'),
          )
          return
        }

        const blob = await response.blob()
        if (current !== entry) return // stopped/superseded while reading the audio body

        const objectUrl = URL.createObjectURL(blob)
        entry.objectUrl = objectUrl
        const audio = new window.Audio(objectUrl)
        entry.audio = audio

        audio.onplay = () => {
          if (current === entry) callbacks.onStart?.()
        }
        audio.onended = () => {
          if (current !== entry) return
          current = null
          teardown(entry)
          callbacks.onNaturalEnd?.()
        }
        audio.onerror = () => {
          if (current !== entry) return
          current = null
          teardown(entry)
          callbacks.onError?.(createVoiceError('playback-failed', 'Voice playback failed. Please try again.'))
        }

        // play() rejects if playback is interrupted before it starts (e.g.
        // a near-simultaneous stop()/supersede already called pause()) —
        // the current-entry guard makes that rejection a no-op rather than
        // a spurious onError.
        audio.play()?.catch?.(() => {
          if (current !== entry) return
          current = null
          teardown(entry)
          callbacks.onError?.(createVoiceError('playback-failed', 'Voice playback failed. Please try again.'))
        })
      })
      .catch((error) => {
        if (current !== entry) return // aborted because stopped/superseded — not a real failure
        if (error?.name === 'AbortError') return
        current = null
        teardown(entry)
        callbacks.onError?.(createVoiceError('network-error', 'Could not reach the voice service. Please try again.'))
      })
  }

  function dispose() {
    endCurrent()
  }

  return { isSupported, speak, stop, dispose }
}
