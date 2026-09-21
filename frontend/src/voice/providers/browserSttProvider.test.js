import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createBrowserSttProvider } from './browserSttProvider.js'

class FakeSpeechRecognition {
  constructor() {
    this.lang = null
    this.interimResults = null
    this.maxAlternatives = null
    this.onstart = null
    this.onspeechstart = null
    this.onspeechend = null
    this.onresult = null
    this.onerror = null
    this.onend = null
    this.start = vi.fn()
    this.stop = vi.fn()
    FakeSpeechRecognition.instances.push(this)
  }
}
FakeSpeechRecognition.instances = []

function installFakeSpeechRecognition() {
  FakeSpeechRecognition.instances = []
  globalThis.window = { SpeechRecognition: FakeSpeechRecognition }
}

function resultEvent(transcript) {
  return { results: [[{ transcript }]] }
}

describe('browserSttProvider (fake SpeechRecognition, no real browser API used)', () => {
  beforeEach(() => {
    installFakeSpeechRecognition()
  })

  afterEach(() => {
    delete globalThis.window
  })

  it('reports supported when SpeechRecognition is present', () => {
    expect(createBrowserSttProvider().isSupported).toBe(true)
  })

  it('reports unsupported and calls onError when SpeechRecognition is absent', () => {
    delete globalThis.window
    globalThis.window = {}
    const provider = createBrowserSttProvider()
    const onError = vi.fn()

    expect(provider.isSupported).toBe(false)
    provider.start({ onError })

    expect(onError).toHaveBeenCalledWith(expect.objectContaining({ code: 'unsupported', recoverable: false }))
    expect(FakeSpeechRecognition.instances).toHaveLength(0)
  })

  it('calls onStart, onSpeechDetected, onSpeechEnd as the underlying events fire', () => {
    const provider = createBrowserSttProvider()
    const onStart = vi.fn()
    const onSpeechDetected = vi.fn()
    const onSpeechEnd = vi.fn()
    provider.start({ onStart, onSpeechDetected, onSpeechEnd })

    const recognition = FakeSpeechRecognition.instances[0]
    recognition.onstart()
    recognition.onspeechstart()
    recognition.onspeechend()

    expect(onStart).toHaveBeenCalledOnce()
    expect(onSpeechDetected).toHaveBeenCalledOnce()
    expect(onSpeechEnd).toHaveBeenCalledOnce()
  })

  it('calls onFinal with the transcript, then onStopped, when a result is produced', () => {
    const provider = createBrowserSttProvider()
    const onFinal = vi.fn()
    const onStopped = vi.fn()
    provider.start({ onFinal, onStopped })

    FakeSpeechRecognition.instances[0].onresult(resultEvent('hello world'))

    expect(onFinal).toHaveBeenCalledWith('hello world')
    // Non-continuous recognition always ends right after one result — the
    // attempt is over, so onStopped follows onFinal (see sttProvider.js).
    expect(onStopped).toHaveBeenCalledOnce()
  })

  it('calls onStopped, not onFinal, when a result event carries no transcript', () => {
    const provider = createBrowserSttProvider()
    const onFinal = vi.fn()
    const onStopped = vi.fn()
    provider.start({ onFinal, onStopped })

    FakeSpeechRecognition.instances[0].onresult(resultEvent(''))

    expect(onFinal).not.toHaveBeenCalled()
    expect(onStopped).toHaveBeenCalledOnce()
  })

  it('maps an "aborted" error (an explicit stop) to onStopped, never onError', () => {
    const provider = createBrowserSttProvider()
    const onStopped = vi.fn()
    const onError = vi.fn()
    provider.start({ onStopped, onError })

    FakeSpeechRecognition.instances[0].onerror({ error: 'aborted' })

    expect(onStopped).toHaveBeenCalledOnce()
    expect(onError).not.toHaveBeenCalled()
  })

  it('maps a genuine recognition error to onError with a friendly message', () => {
    const provider = createBrowserSttProvider()
    const onError = vi.fn()
    provider.start({ onError })

    FakeSpeechRecognition.instances[0].onerror({ error: 'no-speech' })

    expect(onError).toHaveBeenCalledWith(
      expect.objectContaining({ code: 'no-speech', recoverable: true, message: expect.stringContaining('try speaking again') }),
    )
  })

  it('onend falls back to onStopped only when nothing else already settled the attempt', () => {
    const provider = createBrowserSttProvider()
    const onStopped = vi.fn()
    provider.start({ onStopped })

    FakeSpeechRecognition.instances[0].onend() // ended with no result and no error at all

    expect(onStopped).toHaveBeenCalledOnce()
  })

  it('onend does not fire a second onStopped after a result already settled the attempt', () => {
    const provider = createBrowserSttProvider()
    const onFinal = vi.fn()
    const onStopped = vi.fn()
    provider.start({ onFinal, onStopped })

    const recognition = FakeSpeechRecognition.instances[0]
    recognition.onresult(resultEvent('done talking'))
    recognition.onend()

    expect(onFinal).toHaveBeenCalledOnce()
    // onresult itself already produced the one onStopped this attempt gets;
    // onend's fallback must not fire a second one.
    expect(onStopped).toHaveBeenCalledOnce()
  })

  it('never starts a second recognition session while one is already active', () => {
    const provider = createBrowserSttProvider()
    provider.start({})
    provider.start({}) // a second call while the first is still active

    expect(FakeSpeechRecognition.instances).toHaveLength(1)
    expect(FakeSpeechRecognition.instances[0].start).toHaveBeenCalledOnce()
  })

  it('stop() calls the underlying recognition.stop()', () => {
    const provider = createBrowserSttProvider()
    provider.start({})
    provider.stop()

    expect(FakeSpeechRecognition.instances[0].stop).toHaveBeenCalledOnce()
  })
})
