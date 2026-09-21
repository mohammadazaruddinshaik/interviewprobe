// The contract every STT provider must satisfy — browser SpeechRecognition
// today, a remote provider (e.g. Deepgram) later. The voice session only
// ever talks to this shape; it never knows which concrete provider it's
// holding.
//
// @typedef {Object} SttStartCallbacks
// @property {() => void} [onStart] - the microphone is now capturing
// @property {() => void} [onSpeechDetected] - the provider believes the
//   candidate has begun speaking (not all providers can distinguish this
//   from "listening with nothing yet" — a provider that can't should simply
//   never call it, rather than calling it unreliably)
// @property {(transcript: string) => void} [onInterim] - a provisional,
//   not-yet-final transcript chunk. Optional: a provider that only supports
//   final results (like the current browser implementation) never calls it.
// @property {() => void} [onSpeechEnd] - the candidate appears to have
//   stopped talking; a final transcript is expected shortly
// @property {(transcript: string) => void} [onFinal] - one finalized
//   transcript chunk (a delta, not an accumulation). A provider that only
//   ever captures one utterance per attempt (the browser implementation)
//   calls this at most once; a provider that supports continuous listening
//   (a remote streaming provider) may call it any number of times across a
//   single start()...stop() attempt, once per chunk of speech finalized —
//   the caller is responsible for accumulating chunks (e.g. appending each
//   to an existing answer), never this contract.
// @property {() => void} [onStopped] - the listening attempt itself has
//   ended — an explicit stop(), the provider's own natural completion (with
//   or without a preceding onFinal), or an ending with no result and no
//   error. Every provider must eventually call this exactly once per
//   attempt once it is truly done capturing; it never implies a transcript
//   was produced, and never implies one wasn't.
// @property {(error: {code: string, message: string, recoverable: boolean}) => void} [onError] -
//   a genuine recognition failure, already normalized (see errors.js)
//
// @typedef {Object} SttProvider
// @property {boolean} isSupported
// @property {(callbacks?: SttStartCallbacks) => void} start - begins a new
//   listening attempt; a provider must never let a second attempt overlap
//   a still-active one
// @property {() => void} stop - the candidate's explicit "I'm done" — ends
//   capture; a final transcript may still arrive via onFinal afterward
// @property {() => void} dispose - stops and releases any provider
//   resources; call once when the owning session ends

export {}
