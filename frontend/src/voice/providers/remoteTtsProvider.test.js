import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createRemoteTtsProvider } from './remoteTtsProvider.js'

class FakeAudio {
  constructor(src) {
    this.src = src
    this.onplay = null
    this.onended = null
    this.onerror = null
    this.paused = true
    this.playCallCount = 0
  }

  play() {
    this.playCallCount += 1
    this.paused = false
    return Promise.resolve()
  }

  pause() {
    this.paused = true
  }
}

function fakeOkResponse(blob = { size: 4 }) {
  return { ok: true, status: 200, blob: () => Promise.resolve(blob) }
}

function installFakeEnvironment() {
  globalThis.window = { Audio: FakeAudio }
  globalThis.fetch = vi.fn(() => Promise.resolve(fakeOkResponse()))
  globalThis.URL.createObjectURL = vi.fn(() => 'blob:fake-url')
  globalThis.URL.revokeObjectURL = vi.fn()
  return { fetch: globalThis.fetch }
}

// Waits for the fetch()...then() microtask chain inside speak() to settle,
// without depending on real timers or a real network/Audio implementation.
async function flush() {
  await Promise.resolve()
  await Promise.resolve()
  await Promise.resolve()
}

describe('remoteTtsProvider (fake fetch + Audio, no real network or Azure call)', () => {
  let env

  beforeEach(() => {
    env = installFakeEnvironment()
  })

  afterEach(() => {
    delete globalThis.window
    delete globalThis.fetch
    vi.restoreAllMocks()
  })

  it('reports supported when fetch/Audio/AbortController are present', () => {
    const provider = createRemoteTtsProvider()
    expect(provider.isSupported).toBe(true)
  })

  it('reports unsupported and calls onError when window.Audio is absent', () => {
    globalThis.window = {}
    const provider = createRemoteTtsProvider()
    const onError = vi.fn()

    expect(provider.isSupported).toBe(false)
    provider.speak('hello', { onError })

    expect(onError).toHaveBeenCalledWith(expect.objectContaining({ code: 'unsupported', recoverable: false }))
    expect(env.fetch).not.toHaveBeenCalled()
  })

  it('does nothing for empty text', () => {
    const provider = createRemoteTtsProvider()
    provider.speak('', { onStart: vi.fn() })
    expect(env.fetch).not.toHaveBeenCalled()
  })

  it('POSTs { text, voice: "default" } to the voice/tts endpoint, no Azure identifiers', () => {
    const provider = createRemoteTtsProvider()
    provider.speak('Explain how a hash map works.', {})

    expect(env.fetch).toHaveBeenCalledOnce()
    const [url, options] = env.fetch.mock.calls[0]
    expect(url.endsWith('/voice/tts')).toBe(true)
    expect(options.method).toBe('POST')
    expect(JSON.parse(options.body)).toEqual({ text: 'Explain how a hash map works.', voice: 'default' })
  })

  it('fetches the audio and creates a playable object URL from the response body', async () => {
    const provider = createRemoteTtsProvider()
    provider.speak('hello', {})
    await flush()

    expect(globalThis.URL.createObjectURL).toHaveBeenCalledOnce()
  })

  it('a genuine playback failure fires onError, never onStopped', async () => {
    let capturedAudio = null
    class CapturingAudio extends FakeAudio {
      constructor(src) {
        super(src)
        capturedAudio = this
      }
    }
    globalThis.window = { Audio: CapturingAudio }

    const provider = createRemoteTtsProvider()
    const onError = vi.fn()
    const onStopped = vi.fn()
    provider.speak('hello', { onError, onStopped })
    await flush()

    capturedAudio.onerror(new Event('error'))

    expect(onError).toHaveBeenCalledWith(expect.objectContaining({ code: 'playback-failed' }))
    expect(onStopped).not.toHaveBeenCalled()
  })

  it('playback finishing naturally fires onNaturalEnd, never onStopped', async () => {
    let capturedAudio = null
    class CapturingAudio extends FakeAudio {
      constructor(src) {
        super(src)
        capturedAudio = this
      }
    }
    globalThis.window = { Audio: CapturingAudio }

    const provider = createRemoteTtsProvider()
    const onNaturalEnd = vi.fn()
    const onStopped = vi.fn()
    provider.speak('hello', { onNaturalEnd, onStopped })
    await flush()

    capturedAudio.onended()

    expect(onNaturalEnd).toHaveBeenCalledOnce()
    expect(onStopped).not.toHaveBeenCalled()
  })

  it('starting playback fires onStart', async () => {
    let capturedAudio = null
    class CapturingAudio extends FakeAudio {
      constructor(src) {
        super(src)
        capturedAudio = this
      }
    }
    globalThis.window = { Audio: CapturingAudio }

    const provider = createRemoteTtsProvider()
    const onStart = vi.fn()
    provider.speak('hello', { onStart })
    await flush()

    capturedAudio.onplay()

    expect(onStart).toHaveBeenCalledOnce()
  })

  it('stop() while audio is playing fires onStopped, pauses playback, never fires onNaturalEnd', async () => {
    let capturedAudio = null
    class CapturingAudio extends FakeAudio {
      constructor(src) {
        super(src)
        capturedAudio = this
      }
    }
    globalThis.window = { Audio: CapturingAudio }

    const provider = createRemoteTtsProvider()
    const onNaturalEnd = vi.fn()
    const onStopped = vi.fn()
    provider.speak('hello', { onNaturalEnd, onStopped })
    await flush()
    capturedAudio.onplay()

    provider.stop()

    expect(onStopped).toHaveBeenCalledOnce()
    expect(onNaturalEnd).not.toHaveBeenCalled()
    expect(capturedAudio.paused).toBe(true)

    // A late 'ended' event from the now-stopped audio must be inert.
    capturedAudio.onended?.()
    expect(onNaturalEnd).not.toHaveBeenCalled()
  })

  it('stop() while the fetch is still in flight aborts it and fires onStopped, with no later callback', async () => {
    let resolveFetch
    env.fetch.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveFetch = resolve
        }),
    )

    const provider = createRemoteTtsProvider()
    const onStart = vi.fn()
    const onStopped = vi.fn()
    const onError = vi.fn()
    provider.speak('hello', { onStart, onStopped, onError })

    provider.stop()
    expect(onStopped).toHaveBeenCalledOnce()

    // The request eventually resolves after being stopped — must be inert.
    resolveFetch(fakeOkResponse())
    await flush()

    expect(onStart).not.toHaveBeenCalled()
    expect(onError).not.toHaveBeenCalled()
    expect(onStopped).toHaveBeenCalledOnce()
  })

  it('a second speak() supersedes the first: first gets onStopped, only the second produces further callbacks', async () => {
    const capturedAudios = []
    class CapturingAudio extends FakeAudio {
      constructor(src) {
        super(src)
        capturedAudios.push(this)
      }
    }
    globalThis.window = { Audio: CapturingAudio }

    const provider = createRemoteTtsProvider()
    const first = { onNaturalEnd: vi.fn(), onStopped: vi.fn(), onStart: vi.fn() }
    provider.speak('first', first)
    await flush()
    capturedAudios[0].onplay()

    const second = { onNaturalEnd: vi.fn(), onStopped: vi.fn(), onStart: vi.fn() }
    provider.speak('second', second)

    expect(first.onStopped).toHaveBeenCalledOnce()
    expect(capturedAudios[0].paused).toBe(true)

    await flush()
    capturedAudios[1].onplay()
    capturedAudios[1].onended()

    // The first attempt's audio firing late events must be inert.
    capturedAudios[0].onended?.()

    expect(second.onStart).toHaveBeenCalledOnce()
    expect(second.onNaturalEnd).toHaveBeenCalledOnce()
    expect(first.onNaturalEnd).not.toHaveBeenCalled()
  })

  it('a non-ok HTTP response fires onError without creating an Audio element', async () => {
    env.fetch.mockResolvedValue({ ok: false, status: 500 })

    const provider = createRemoteTtsProvider()
    const onError = vi.fn()
    provider.speak('hello', { onError })
    await flush()

    expect(onError).toHaveBeenCalledWith(expect.objectContaining({ code: 'service-error' }))
    expect(globalThis.URL.createObjectURL).not.toHaveBeenCalled()
  })

  it('a network failure fires onError with a network-error code', async () => {
    env.fetch.mockRejectedValue(new TypeError('Failed to fetch'))

    const provider = createRemoteTtsProvider()
    const onError = vi.fn()
    provider.speak('hello', { onError })
    await flush()

    expect(onError).toHaveBeenCalledWith(expect.objectContaining({ code: 'network-error' }))
  })

  it('dispose() stops any in-flight/playing attempt and releases the object URL', async () => {
    let capturedAudio = null
    class CapturingAudio extends FakeAudio {
      constructor(src) {
        super(src)
        capturedAudio = this
      }
    }
    globalThis.window = { Audio: CapturingAudio }

    const provider = createRemoteTtsProvider()
    const onStopped = vi.fn()
    provider.speak('hello', { onStopped })
    await flush()
    capturedAudio.onplay()

    provider.dispose()

    expect(onStopped).toHaveBeenCalledOnce()
    expect(capturedAudio.paused).toBe(true)
    expect(globalThis.URL.revokeObjectURL).toHaveBeenCalledWith('blob:fake-url')
  })
})
