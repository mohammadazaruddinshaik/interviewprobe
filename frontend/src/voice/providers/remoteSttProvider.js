import { createVoiceError } from '../errors.js'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

// Fixed, internal implementation constants — never user-selectable, never
// sourced from a backend setting. Unlike the TTS voice choice (Task 40),
// these can't be hidden behind the backend: the browser streams audio
// directly to Deepgram (never proxied through our backend), so it must
// know the model/language/keyterms itself to build its own connection URL.
// `en-IN` is Deepgram's confirmed-supported Indian-English locale for
// nova-3 streaming (developers.deepgram.com/docs/models-languages-overview).
const DEEPGRAM_MODEL = 'nova-3'
const DEEPGRAM_LANGUAGE = 'en-IN'
const DEEPGRAM_LISTEN_URL = 'wss://api.deepgram.com/v1/listen'
const UTTERANCE_END_MS = 1000
const MEDIA_RECORDER_TIMESLICE_MS = 250
const CANDIDATE_MIME_TYPES = ['audio/webm;codecs=opus', 'audio/webm']

// How long stop() waits for Deepgram to gracefully finish after a
// CloseStream request before giving up and closing the connection itself.
// Deepgram normally finalizes and closes well within a few hundred ms; this
// is a generous upper bound so a slow/unresponsive close never makes the
// candidate wait long for their "Finish Answer" click to take effect. Kept
// well under useVoiceInterviewSession's own PROCESSING_TIMEOUT_MS (8s),
// which remains an outer safety net if this somehow never settles.
const GRACEFUL_STOP_TIMEOUT_MS = 1500

// A compact, interview-relevant technical vocabulary boosted via Deepgram's
// Keyterm Prompting (nova-3). Deliberately small and generic — never
// candidate-specific data.
const KEYTERMS = [
  'Redis',
  'PostgreSQL',
  'MongoDB',
  'Qdrant',
  'LangGraph',
  'LangChain',
  'FastAPI',
  'React',
  'Node.js',
  'Express',
  'Python',
  'JavaScript',
  'TypeScript',
  'Kubernetes',
  'Docker',
  'REST',
  'API',
  'RAG',
  'LLM',
  'embedding',
  'vector database',
]

function detectSupport() {
  return (
    typeof window !== 'undefined' &&
    typeof window.WebSocket === 'function' &&
    typeof window.MediaRecorder === 'function' &&
    typeof navigator !== 'undefined' &&
    Boolean(navigator.mediaDevices?.getUserMedia)
  )
}

function pickMimeType() {
  if (typeof window.MediaRecorder?.isTypeSupported !== 'function') return undefined
  try {
    return CANDIDATE_MIME_TYPES.find((type) => window.MediaRecorder.isTypeSupported(type))
  } catch {
    return undefined
  }
}

function buildStreamUrl() {
  const params = new URLSearchParams()
  params.set('model', DEEPGRAM_MODEL)
  params.set('language', DEEPGRAM_LANGUAGE)
  params.set('interim_results', 'true')
  params.set('punctuate', 'true')
  params.set('smart_format', 'true')
  params.set('vad_events', 'true')
  params.set('utterance_end_ms', String(UTTERANCE_END_MS))
  for (const term of KEYTERMS) params.append('keyterm', term)
  return `${DEEPGRAM_LISTEN_URL}?${params.toString()}`
}

// The short-lived token is passed via the WebSocket subprotocol handshake
// (`Sec-WebSocket-Protocol: bearer, <token>`) — the browser's native
// WebSocket API cannot set an Authorization header, so this is the only
// way to authenticate without putting the token in the URL. Verified live
// against Deepgram's API: the `?access_token=` query-parameter scheme (an
// older workaround some third-party discussions suggested) is rejected
// with HTTP 401 for tokens minted by /v1/auth/grant — Deepgram expects the
// `bearer` subprotocol for these short-lived tokens specifically (`token`
// is for permanent API keys only, and is also rejected here).
function buildSubprotocols(accessToken) {
  return ['bearer', accessToken]
}

function mapGetUserMediaError(err) {
  const name = err?.name
  if (name === 'NotAllowedError' || name === 'PermissionDeniedError' || name === 'SecurityError') {
    return createVoiceError(
      'permission-denied',
      'Microphone access was denied. Allow microphone access in your browser to use voice input.',
    )
  }
  if (name === 'NotFoundError' || name === 'DevicesNotFoundError') {
    return createVoiceError('no-microphone', 'No microphone was found. Check your device and try again.', {
      recoverable: false,
    })
  }
  return createVoiceError('microphone-error', 'Voice input failed. Please try again or type your answer.')
}

// The Deepgram-backed implementation of the SttProvider contract
// (sttProvider.js) — this module is the ONLY place that knows streaming
// happens via Deepgram; everything it returns matches the same SttProvider
// shape any implementation of this contract must. The permanent Deepgram
// key never reaches this code: only a short-lived token fetched from this
// app's own backend (POST /voice/stt/token) is ever held here, and only for the
// duration of one connection attempt.
export function createRemoteSttProvider() {
  const isSupported = detectSupport()

  // At most one attempt (permission request + token fetch + WebSocket +
  // MediaRecorder) is ever "current". Every async continuation and every
  // socket/recorder event checks `current === entry` before doing anything
  // observable — the same identity-guard shape remoteTtsProvider.js uses,
  // just spanning a mic-permission prompt, a token exchange, and a
  // persistent connection instead of one fetch.
  let current = null

  function teardownMedia(entry) {
    if (entry.recorder) {
      entry.recorder.ondataavailable = null
      try {
        if (entry.recorder.state !== 'inactive') entry.recorder.stop()
      } catch {
        // Already stopped — nothing to do.
      }
    }
    entry.stream?.getTracks().forEach((track) => track.stop())
  }

  function teardownWs(entry) {
    if (entry.ws) {
      entry.ws.onopen = null
      entry.ws.onmessage = null
      entry.ws.onerror = null
      entry.ws.onclose = null
      try {
        if (entry.ws.readyState === window.WebSocket.OPEN || entry.ws.readyState === window.WebSocket.CONNECTING) {
          entry.ws.close()
        }
      } catch {
        // Already closing/closed — nothing to do.
      }
    }
  }

  function teardown(entry) {
    teardownMedia(entry)
    teardownWs(entry)
  }

  // The single place an attempt is ever actually torn down, its onStopped
  // fired, and any pending stop() promise resolved — guarded by
  // entry.settled so it can safely run from more than one path (e.g. a
  // superseding start()/dispose() arriving while a graceful stop() is still
  // mid-wait) without ever double-firing onStopped, resolving a fabricated
  // transcript, or leaving an earlier stop() caller awaiting a promise that
  // would otherwise only resolve when its own now-irrelevant grace timer
  // eventually elapses.
  function finalizeStop(entry) {
    if (entry.settled) return
    entry.settled = true
    if (current === entry) current = null
    if (entry.stopTimeoutId !== undefined) clearTimeout(entry.stopTimeoutId)
    teardown(entry)
    entry.callbacks.onStopped?.()
    entry.resolveStopPromise?.()
  }

  // Abandons whatever attempt is currently active immediately, with no
  // grace period — used when a new start() supersedes a still-active one
  // and by dispose(). The old attempt is being discarded outright (its
  // transcript no longer matters, e.g. the question changed), so there is
  // nothing worth waiting for, unlike the explicit stop() below.
  function endCurrent() {
    if (!current) return
    finalizeStop(current)
  }

  // The candidate's explicit "I'm done" (sttProvider.js's stop() contract:
  // "a final transcript may still arrive via onFinal afterward"). Recording
  // stops immediately — no more audio is ever sent — but the connection is
  // kept open just long enough for Deepgram to finish classifying audio
  // already sent and deliver a trailing final transcript, by asking it to
  // close gracefully (Deepgram's documented CloseStream message) instead of
  // abruptly closing the socket, which would otherwise silently drop
  // whatever final Deepgram was still about to send. Bounded by
  // GRACEFUL_STOP_TIMEOUT_MS so this never hangs if Deepgram doesn't
  // respond. Returns a promise resolving once onStopped has fired, so a
  // caller that needs to know the transcript has fully settled (e.g. before
  // submitting an answer) can await it; callers that don't care can ignore
  // the return value exactly as before.
  function stop() {
    if (!isSupported || !current) return Promise.resolve()
    const entry = current

    teardownMedia(entry)

    if (entry.settled) return Promise.resolve()
    // A stop() is already in flight for this entry (e.g. a duplicate click,
    // or the PROCESSING-timeout's own retry landing while the first attempt
    // is still gracefully closing) — share its outcome rather than sending
    // a second CloseStream and racing a second independent timer against
    // the first.
    if (entry.stopPromise) return entry.stopPromise

    if (!entry.ws || entry.ws.readyState !== window.WebSocket.OPEN) {
      finalizeStop(entry)
      return Promise.resolve()
    }

    entry.stopPromise = new Promise((resolve) => {
      entry.resolveStopPromise = resolve
      entry.stopTimeoutId = setTimeout(() => finalizeStop(entry), GRACEFUL_STOP_TIMEOUT_MS)
      // Deepgram finalizes any pending audio and closes the connection
      // itself in response — that close is what finalizeStop below reacts
      // to. onmessage is deliberately left untouched here so a trailing
      // final Results message during this wait still reaches
      // callbacks.onFinal exactly as it would mid-attempt. Every path here
      // (a real close, an error, the timeout, or a superseding start()/
      // dispose() calling finalizeStop directly) converges on the same
      // finalizeStop, so this promise is guaranteed to resolve exactly
      // once, promptly, regardless of which one actually happens.
      entry.ws.onclose = () => finalizeStop(entry)
      entry.ws.onerror = () => finalizeStop(entry)
      try {
        entry.ws.send(JSON.stringify({ type: 'CloseStream' }))
      } catch {
        finalizeStop(entry)
      }
    })
    return entry.stopPromise
  }

  async function start(callbacks = {}) {
    if (!isSupported) {
      callbacks.onError?.(
        createVoiceError('unsupported', 'Voice input is not supported in this browser. Try Chrome or Edge, or type your answer.', {
          recoverable: false,
        }),
      )
      return
    }

    endCurrent()
    const entry = { stream: null, recorder: null, ws: null, callbacks, settled: false }
    current = entry

    // Microphone permission is requested here, and only here — never
    // earlier (page load, voice mode toggling), matching every other
    // provider's contract.
    let stream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch (err) {
      if (current !== entry) return
      current = null
      callbacks.onError?.(mapGetUserMediaError(err))
      return
    }
    if (current !== entry) {
      stream.getTracks().forEach((track) => track.stop())
      return
    }
    entry.stream = stream

    let tokenData
    try {
      const response = await fetch(`${API_BASE_URL}/voice/stt/token`, { method: 'POST' })
      if (!response.ok) {
        callbacks.onError?.(
          createVoiceError('authorization-failed', 'Voice input is not available right now. Please try again.'),
        )
        current = null
        teardown(entry)
        return
      }
      const body = await response.json()
      tokenData = body.data
    } catch {
      if (current !== entry) return
      current = null
      teardown(entry)
      callbacks.onError?.(createVoiceError('network-error', 'Could not reach the voice service. Please try again.'))
      return
    }
    if (current !== entry) {
      teardown(entry)
      return
    }

    const ws = new window.WebSocket(buildStreamUrl(), buildSubprotocols(tokenData.access_token))
    entry.ws = ws

    ws.onopen = () => {
      if (current !== entry) return
      const mimeType = pickMimeType()
      const recorder = mimeType ? new window.MediaRecorder(entry.stream, { mimeType }) : new window.MediaRecorder(entry.stream)
      entry.recorder = recorder
      recorder.ondataavailable = (event) => {
        if (current !== entry) return
        if (event.data.size > 0 && ws.readyState === window.WebSocket.OPEN) ws.send(event.data)
      }
      recorder.start(MEDIA_RECORDER_TIMESLICE_MS)
      callbacks.onStart?.()
    }

    ws.onmessage = (event) => {
      if (current !== entry) return
      let data
      try {
        data = JSON.parse(event.data)
      } catch {
        return
      }
      // Deepgram's raw message shape never leaves this function — only the
      // provider-neutral callbacks below.
      if (data.type === 'SpeechStarted') {
        callbacks.onSpeechDetected?.()
        return
      }
      if (data.type === 'UtteranceEnd') {
        callbacks.onSpeechEnd?.()
        return
      }
      if (data.type === 'Results') {
        const transcript = data.channel?.alternatives?.[0]?.transcript ?? ''
        if (!transcript) return
        if (data.is_final) {
          callbacks.onFinal?.(transcript) // one delta chunk — see sttProvider.js
        } else {
          callbacks.onInterim?.(transcript)
        }
      }
    }

    ws.onerror = () => {
      if (current !== entry) return
      current = null
      teardown(entry)
      callbacks.onError?.(createVoiceError('connection-error', 'Voice input connection failed. Please try again.'))
    }

    ws.onclose = (event) => {
      if (current !== entry) return
      current = null
      teardown(entry)
      // 1008 (policy violation) is Deepgram's close code for an invalid/
      // expired/rejected token — everything else unsolicited is a lost
      // connection. Neither case invents a transcript.
      if (event.code === 1008) {
        callbacks.onError?.(
          createVoiceError('authentication-failed', 'Voice input could not be authorized. Please try again.'),
        )
      } else {
        callbacks.onError?.(
          createVoiceError('connection-lost', 'The voice input connection was lost. Please try again.'),
        )
      }
    }
  }

  function dispose() {
    endCurrent()
  }

  return { isSupported, start, stop, dispose }
}
