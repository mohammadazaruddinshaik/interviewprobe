// The contract every TTS provider must satisfy — currently one concrete
// implementation (Azure Speech, remoteTtsProvider.js), kept behind this
// abstraction rather than called directly so the voice session only ever
// talks to this shape and never knows which concrete provider it's
// holding.
//
// @typedef {Object} TtsSpeakCallbacks
// @property {() => void} [onStart] - playback has audibly begun
// @property {() => void} [onNaturalEnd] - the utterance finished on its own.
//   Must NEVER fire for a stop()-triggered cancellation, a superseded
//   utterance, or an error — that distinction is the whole point of having
//   a separate onStopped/onError callback.
// @property {() => void} [onStopped] - playback ended because something
//   cancelled it (an explicit stop(), a new speak() superseding it, or a
//   cancellation the provider can't treat as a real failure).
// @property {(error: {code: string, message: string, recoverable: boolean}) => void} [onError] -
//   a genuine synthesis failure, already normalized (see errors.js)
//
// @typedef {Object} TtsProvider
// @property {boolean} isSupported
// @property {(text: string, callbacks?: TtsSpeakCallbacks) => void} speak -
//   starts a new utterance, implicitly cancelling any utterance already in
//   flight first (at most one utterance is ever active)
// @property {() => void} stop - cancels the in-flight utterance, if any;
//   triggers onStopped, never onNaturalEnd
// @property {() => void} dispose - stops and releases any provider
//   resources; call once when the owning session ends

export {}
