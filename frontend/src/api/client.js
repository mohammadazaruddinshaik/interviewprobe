const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

// Generic, user-facing fallback messages by HTTP status. Used whenever the
// backend's response body doesn't carry a more specific message (see
// `extractErrorInfo` below) — e.g. an unhandled 500 that comes back as
// plain text, not the `{ error: { code, message } }` envelope.
const FALLBACK_MESSAGES = {
  400: 'Something went wrong with that request. Please try again.',
  404: "We couldn't find what you were looking for.",
  409: 'That action could not be completed right now. Please try again.',
  422: 'Some of the submitted information was not valid.',
  429: "You're sending requests too quickly. Please wait a moment and try again.",
  500: 'Something went wrong. Please try again.',
  503: "InterviewProbe couldn't reach the interview service. Please try again.",
}

const NETWORK_ERROR_MESSAGE = "InterviewProbe couldn't reach the interview service. Please try again."
const DEFAULT_ERROR_MESSAGE = 'Something went wrong. Please try again.'

export class ApiError extends Error {
  constructor(message, { status, code } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

// The backend uses two different error body shapes depending on where the
// failure happens: domain errors (404/409/422/429/503, registered in
// app/main.py) return `{ error: { code, message } }`, while FastAPI's own
// request validation (raw pydantic errors) returns `{ detail: [...] }`.
// An unhandled exception falls through to a plain-text 500 with no JSON
// body at all. This picks a safe, specific message out of whichever shape
// actually comes back, and returns null when it can't.
function extractErrorInfo(body) {
  if (!body || typeof body !== 'object') return null

  if (body.error && typeof body.error.message === 'string') {
    return { message: body.error.message, code: body.error.code }
  }

  if (typeof body.detail === 'string') {
    return { message: body.detail, code: undefined }
  }

  if (Array.isArray(body.detail) && body.detail.length > 0) {
    const [first] = body.detail
    if (first && typeof first.msg === 'string') {
      return { message: first.msg, code: undefined }
    }
  }

  return null
}

async function request(path, { method = 'GET', body, headers } = {}) {
  let response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: { 'Content-Type': 'application/json', ...headers },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch {
    // fetch() throws for network failures and CORS rejections alike —
    // both are indistinguishable from the browser's perspective, and both
    // genuinely mean "the interview service could not be reached".
    throw new ApiError(NETWORK_ERROR_MESSAGE, { status: 0 })
  }

  const text = await response.text()
  let parsedBody = null
  if (text) {
    try {
      parsedBody = JSON.parse(text)
    } catch {
      parsedBody = null
    }
  }

  if (!response.ok) {
    const info = extractErrorInfo(parsedBody)
    const message = info?.message ?? FALLBACK_MESSAGES[response.status] ?? DEFAULT_ERROR_MESSAGE
    throw new ApiError(message, { status: response.status, code: info?.code })
  }

  return parsedBody
}

export const apiClient = {
  get: (path) => request(path),
  post: (path, body, options) => request(path, { method: 'POST', body, headers: options?.headers }),
}
