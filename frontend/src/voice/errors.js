// The one error shape every provider adapter normalizes into before it ever
// reaches the reducer or the UI — callers never see a raw DOM/browser
// exception or a provider-specific error object.
//
// @typedef {Object} VoiceError
// @property {string} code - a short, stable identifier (e.g. 'not-allowed')
// @property {string} message - candidate-facing, already friendly
// @property {boolean} recoverable - whether retrying the same action again
//   might succeed (false for "this browser doesn't support voice at all")

export function createVoiceError(code, message, { recoverable = true } = {}) {
  return { code, message, recoverable }
}
