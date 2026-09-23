import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createRemoteSttProvider } from './remoteSttProvider.js'

class FakeMediaRecorder {
  constructor(stream, options) {
    this.stream = stream
    this.options = options
    this.state = 'inactive'
    this.ondataavailable = null
    this.start = vi.fn((timeslice) => {
      this.state = 'recording'
      this.timeslice = timeslice
    })
    this.stop = vi.fn(() => {
      this.state = 'inactive'
    })
    FakeMediaRecorder.instances.push(this)
  }
}
FakeMediaRecorder.instances = []
FakeMediaRecorder.isTypeSupported = vi.fn(() => true)

class FakeWebSocket {
  constructor(url, protocols) {
    this.url = url
    this.protocols = protocols
    this.readyState = FakeWebSocket.CONNECTING
    this.onopen = null
    this.onmessage = null
    this.onerror = null
    this.onclose = null
    this.sentMessages = []
    this.send = vi.fn((data) => this.sentMessages.push(data))
    this.close = vi.fn(() => {
      this.readyState = FakeWebSocket.CLOSED
    })
    FakeWebSocket.instances.push(this)
  }
}
FakeWebSocket.CONNECTING = 0
FakeWebSocket.OPEN = 1
FakeWebSocket.CLOSING = 2
FakeWebSocket.CLOSED = 3
FakeWebSocket.instances = []

function makeFakeStream() {
  const track = { stop: vi.fn() }
  return { getTracks: () => [track], _track: track }
}

function deferred() {
  let resolve
  let reject
  const promise = new Promise((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

function fakeTokenResponse(overrides = {}) {
  return {
    ok: true,
    json: () => Promise.resolve({ data: { access_token: 'temp-jwt', expires_in: 30, ...overrides } }),
  }
}

function installFakeEnvironment({ getUserMedia } = {}) {
  FakeMediaRecorder.instances = []
  FakeWebSocket.instances = []
  globalThis.window = { WebSocket: FakeWebSocket, MediaRecorder: FakeMediaRecorder }
  globalThis.navigator = {
    mediaDevices: { getUserMedia: getUserMedia ?? vi.fn(() => Promise.resolve(makeFakeStream())) },
  }
  globalThis.fetch = vi.fn(() => Promise.resolve(fakeTokenResponse()))
  return { fetch: globalThis.fetch }
}

async function flush() {
  await Promise.resolve()
  await Promise.resolve()
  await Promise.resolve()
  await Promise.resolve()
}

function openSocket(ws) {
  ws.readyState = FakeWebSocket.OPEN
  ws.onopen()
}

function sendMessage(ws, payload) {
  ws.onmessage({ data: JSON.stringify(payload) })
}

describe('remoteSttProvider (fake getUserMedia/MediaRecorder/WebSocket, no real mic/network/Deepgram)', () => {
  let env

  beforeEach(() => {
    env = installFakeEnvironment()
  })

  afterEach(() => {
    delete globalThis.window
    delete globalThis.navigator
    delete globalThis.fetch
    vi.restoreAllMocks()
  })

  it('1. reports supported when WebSocket/MediaRecorder/getUserMedia are present', () => {
    expect(createRemoteSttProvider().isSupported).toBe(true)
  })

  it('1b. reports unsupported and calls onError when getUserMedia is absent, without touching the mic/network', async () => {
    globalThis.navigator = { mediaDevices: {} }
    const provider = createRemoteSttProvider()
    const onError = vi.fn()

    expect(provider.isSupported).toBe(false)
    await provider.start({ onError })

    expect(onError).toHaveBeenCalledWith(expect.objectContaining({ code: 'unsupported', recoverable: false }))
    expect(env.fetch).not.toHaveBeenCalled()
  })

  it('2. start obtains authorization from the backend token endpoint', async () => {
    const provider = createRemoteSttProvider()
    await provider.start({})
    await flush()

    expect(env.fetch).toHaveBeenCalledOnce()
    const [url, options] = env.fetch.mock.calls[0]
    expect(url.endsWith('/voice/stt/token')).toBe(true)
    expect(options.method).toBe('POST')
  })

  it('3. microphone permission is requested only when start() is called', async () => {
    const getUserMedia = vi.fn(() => Promise.resolve(makeFakeStream()))
    env = installFakeEnvironment({ getUserMedia })
    createRemoteSttProvider() // constructing the provider alone must not touch the mic
    expect(getUserMedia).not.toHaveBeenCalled()

    const provider = createRemoteSttProvider()
    await provider.start({})

    expect(getUserMedia).toHaveBeenCalledOnce()
  })

  it('4. a streaming connection is established with the expected model/language/keyterm params, and the token via the bearer subprotocol', async () => {
    const provider = createRemoteSttProvider()
    await provider.start({})
    await flush()

    expect(FakeWebSocket.instances).toHaveLength(1)
    const instance = FakeWebSocket.instances[0]
    const url = new URL(instance.url)
    expect(url.protocol).toBe('wss:')
    expect(url.searchParams.get('model')).toBe('nova-3')
    expect(url.searchParams.get('language')).toBe('en-IN')
    expect(url.searchParams.getAll('keyterm').length).toBeGreaterThan(0)
    // The token is never placed in the URL (Deepgram rejects that scheme
    // with 401 for tokens minted by /v1/auth/grant, verified against the
    // live API) — it goes through the Sec-WebSocket-Protocol subprotocol
    // list instead, which the browser sends as part of the handshake.
    expect(url.searchParams.has('access_token')).toBe(false)
    expect(instance.protocols).toEqual(['bearer', 'temp-jwt'])
  })

  it('5. onStart fires once the connection opens and recording begins', async () => {
    const provider = createRemoteSttProvider()
    const onStart = vi.fn()
    await provider.start({ onStart })
    await flush()

    openSocket(FakeWebSocket.instances[0])

    expect(onStart).toHaveBeenCalledOnce()
    expect(FakeMediaRecorder.instances[0].start).toHaveBeenCalledWith(250)
  })

  it('6. an interim Results message fires onInterim', async () => {
    const provider = createRemoteSttProvider()
    const onInterim = vi.fn()
    await provider.start({ onInterim })
    await flush()
    openSocket(FakeWebSocket.instances[0])

    sendMessage(FakeWebSocket.instances[0], {
      type: 'Results',
      is_final: false,
      channel: { alternatives: [{ transcript: 'I would first' }] },
    })

    expect(onInterim).toHaveBeenCalledWith('I would first')
  })

  it('7. a SpeechStarted message fires onSpeechDetected', async () => {
    const provider = createRemoteSttProvider()
    const onSpeechDetected = vi.fn()
    await provider.start({ onSpeechDetected })
    await flush()
    openSocket(FakeWebSocket.instances[0])

    sendMessage(FakeWebSocket.instances[0], { type: 'SpeechStarted' })

    expect(onSpeechDetected).toHaveBeenCalledOnce()
  })

  it('8. a final Results message fires onFinal with just that chunk', async () => {
    const provider = createRemoteSttProvider()
    const onFinal = vi.fn()
    await provider.start({ onFinal })
    await flush()
    openSocket(FakeWebSocket.instances[0])

    sendMessage(FakeWebSocket.instances[0], {
      type: 'Results',
      is_final: true,
      channel: { alternatives: [{ transcript: 'Redis uses SETNX for locking' }] },
    })

    expect(onFinal).toHaveBeenCalledWith('Redis uses SETNX for locking')
  })

  it('8b. an UtteranceEnd message fires onSpeechEnd', async () => {
    const provider = createRemoteSttProvider()
    const onSpeechEnd = vi.fn()
    await provider.start({ onSpeechEnd })
    await flush()
    openSocket(FakeWebSocket.instances[0])

    sendMessage(FakeWebSocket.instances[0], { type: 'UtteranceEnd' })

    expect(onSpeechEnd).toHaveBeenCalledOnce()
  })

  it('8c. multiple final chunks in one attempt each fire onFinal — the provider never accumulates them itself', async () => {
    const provider = createRemoteSttProvider()
    const onFinal = vi.fn()
    await provider.start({ onFinal })
    await flush()
    const ws = FakeWebSocket.instances[0]
    openSocket(ws)

    sendMessage(ws, { type: 'Results', is_final: true, channel: { alternatives: [{ transcript: 'first chunk' }] } })
    sendMessage(ws, { type: 'Results', is_final: true, channel: { alternatives: [{ transcript: 'second chunk' }] } })

    expect(onFinal).toHaveBeenNthCalledWith(1, 'first chunk')
    expect(onFinal).toHaveBeenNthCalledWith(2, 'second chunk')
  })

  it('9. explicit stop fires onStopped', async () => {
    const provider = createRemoteSttProvider()
    const onStopped = vi.fn()
    await provider.start({ onStopped })
    await flush()
    openSocket(FakeWebSocket.instances[0])

    provider.stop()

    expect(onStopped).toHaveBeenCalledOnce()
  })

  it('10. explicit stop does not produce a fake final transcript', async () => {
    const provider = createRemoteSttProvider()
    const onFinal = vi.fn()
    const onStopped = vi.fn()
    await provider.start({ onFinal, onStopped })
    await flush()
    openSocket(FakeWebSocket.instances[0])

    provider.stop()

    expect(onFinal).not.toHaveBeenCalled()
    expect(onStopped).toHaveBeenCalledOnce()
  })

  it('10b. a final delivered immediately before stop is still delivered normally', async () => {
    const provider = createRemoteSttProvider()
    const onFinal = vi.fn()
    const onStopped = vi.fn()
    await provider.start({ onFinal, onStopped })
    await flush()
    const ws = FakeWebSocket.instances[0]
    openSocket(ws)

    sendMessage(ws, { type: 'Results', is_final: true, channel: { alternatives: [{ transcript: 'last words' }] } })
    provider.stop()

    expect(onFinal).toHaveBeenCalledWith('last words')
    expect(onStopped).toHaveBeenCalledOnce()
  })

  it('11. stop() releases the microphone tracks', async () => {
    const provider = createRemoteSttProvider()
    await provider.start({})
    await flush()
    openSocket(FakeWebSocket.instances[0])
    const track = FakeMediaRecorder.instances[0].stream._track

    provider.stop()

    expect(track.stop).toHaveBeenCalledOnce()
  })

  it('12. stop() closes the streaming connection', async () => {
    const provider = createRemoteSttProvider()
    await provider.start({})
    await flush()
    openSocket(FakeWebSocket.instances[0])

    provider.stop()

    expect(FakeWebSocket.instances[0].close).toHaveBeenCalledOnce()
  })

  it('13. a WebSocket error maps to a connection-error, never onStopped/onFinal', async () => {
    const provider = createRemoteSttProvider()
    const onError = vi.fn()
    const onStopped = vi.fn()
    await provider.start({ onError, onStopped })
    await flush()
    const ws = FakeWebSocket.instances[0]
    openSocket(ws)

    ws.onerror(new Event('error'))

    expect(onError).toHaveBeenCalledWith(expect.objectContaining({ code: 'connection-error' }))
    expect(onStopped).not.toHaveBeenCalled()
  })

  it('14. a close with code 1008 maps to an authentication failure', async () => {
    const provider = createRemoteSttProvider()
    const onError = vi.fn()
    await provider.start({ onError })
    await flush()
    const ws = FakeWebSocket.instances[0]
    openSocket(ws)

    ws.onclose({ code: 1008 })

    expect(onError).toHaveBeenCalledWith(expect.objectContaining({ code: 'authentication-failed' }))
  })

  it('15. microphone permission denial maps to permission-denied, without ever fetching a token', async () => {
    const getUserMedia = vi.fn(() => Promise.reject(Object.assign(new Error('denied'), { name: 'NotAllowedError' })))
    env = installFakeEnvironment({ getUserMedia })
    const provider = createRemoteSttProvider()
    const onError = vi.fn()

    await provider.start({ onError })

    expect(onError).toHaveBeenCalledWith(expect.objectContaining({ code: 'permission-denied' }))
    expect(env.fetch).not.toHaveBeenCalled()
  })

  it('16. an unsolicited close with a non-1008 code maps to connection-lost', async () => {
    const provider = createRemoteSttProvider()
    const onError = vi.fn()
    await provider.start({ onError })
    await flush()
    const ws = FakeWebSocket.instances[0]
    openSocket(ws)

    ws.onclose({ code: 1006 })

    expect(onError).toHaveBeenCalledWith(expect.objectContaining({ code: 'connection-lost', recoverable: true }))
  })

  it('16b. a token endpoint failure maps to authorization-failed', async () => {
    env.fetch.mockResolvedValue({ ok: false, status: 500 })
    const provider = createRemoteSttProvider()
    const onError = vi.fn()

    await provider.start({ onError })
    await flush()

    expect(onError).toHaveBeenCalledWith(expect.objectContaining({ code: 'authorization-failed' }))
    expect(FakeWebSocket.instances).toHaveLength(0)
  })

  it('16c. a network failure while fetching the token maps to network-error', async () => {
    env.fetch.mockRejectedValue(new TypeError('Failed to fetch'))
    const provider = createRemoteSttProvider()
    const onError = vi.fn()

    await provider.start({ onError })
    await flush()

    expect(onError).toHaveBeenCalledWith(expect.objectContaining({ code: 'network-error' }))
  })

  it('17. a second start() supersedes the first: the first gets onStopped, only the second proceeds', async () => {
    const provider = createRemoteSttProvider()
    const first = { onStopped: vi.fn(), onStart: vi.fn() }
    await provider.start(first)
    await flush()
    openSocket(FakeWebSocket.instances[0])

    const second = { onStopped: vi.fn(), onStart: vi.fn() }
    const secondStart = provider.start(second)

    expect(first.onStopped).toHaveBeenCalledOnce()
    expect(FakeWebSocket.instances[0].close).toHaveBeenCalledOnce()

    await secondStart
    await flush()
    openSocket(FakeWebSocket.instances[1])

    expect(second.onStart).toHaveBeenCalledOnce()
    // first.onStart legitimately fired once, earlier in this test, from
    // openSocket() on the first connection — it must not fire again.
    expect(first.onStart).toHaveBeenCalledOnce()
  })

  it('18. stale events from a superseded connection are ignored', async () => {
    const provider = createRemoteSttProvider()
    const first = { onFinal: vi.fn(), onStopped: vi.fn() }
    await provider.start(first)
    await flush()
    const firstWs = FakeWebSocket.instances[0]
    openSocket(firstWs)

    const second = { onFinal: vi.fn() }
    await provider.start(second)
    await flush()
    openSocket(FakeWebSocket.instances[1])

    // The stale socket firing late must be inert — its handlers were
    // detached during teardown.
    expect(firstWs.onmessage).toBeNull()
    expect(firstWs.onopen).toBeNull()
  })

  it('19. dispose() stops any in-flight/listening attempt and releases all resources', async () => {
    const provider = createRemoteSttProvider()
    const onStopped = vi.fn()
    await provider.start({ onStopped })
    await flush()
    openSocket(FakeWebSocket.instances[0])
    const track = FakeMediaRecorder.instances[0].stream._track

    provider.dispose()

    expect(onStopped).toHaveBeenCalledOnce()
    expect(track.stop).toHaveBeenCalledOnce()
    expect(FakeWebSocket.instances[0].close).toHaveBeenCalledOnce()
  })

  it('20. stopping while still awaiting microphone permission prevents any later connection/callback', async () => {
    const gate = deferred()
    const getUserMedia = vi.fn(() => gate.promise)
    env = installFakeEnvironment({ getUserMedia })
    const provider = createRemoteSttProvider()
    const onStopped = vi.fn()
    const onStart = vi.fn()
    const onError = vi.fn()

    // start() runs synchronously up to the getUserMedia await, registering
    // itself as the current attempt before suspending — so a stop() called
    // right after (still before permission resolves) does invalidate it.
    const startPromise = provider.start({ onStopped, onStart, onError })
    provider.stop()

    const stream = makeFakeStream()
    gate.resolve(stream)
    await startPromise
    await flush()

    expect(onStopped).toHaveBeenCalledOnce()
    expect(onStart).not.toHaveBeenCalled()
    expect(onError).not.toHaveBeenCalled()
    // The mic was briefly acquired (permission had already been asked for)
    // but must be released immediately once the attempt is known-stale.
    expect(stream._track.stop).toHaveBeenCalledOnce()
    expect(env.fetch).not.toHaveBeenCalled()
    expect(FakeWebSocket.instances).toHaveLength(0)
  })
})
