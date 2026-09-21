import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createBrowserTtsProvider } from './browserTtsProvider.js'

class FakeSpeechSynthesisUtterance {
  constructor(text) {
    this.text = text
    this.voice = null
    this.lang = null
    this.onstart = null
    this.onend = null
    this.onerror = null
  }
}

function installFakeSpeechSynthesis() {
  const fake = {
    speak: vi.fn(),
    cancel: vi.fn(),
    getVoices: vi.fn(() => []),
  }
  globalThis.window = { speechSynthesis: fake, SpeechSynthesisUtterance: FakeSpeechSynthesisUtterance }
  return fake
}

describe('browserTtsProvider (fake SpeechSynthesis, no real browser API used)', () => {
  let fakeSynthesis

  beforeEach(() => {
    fakeSynthesis = installFakeSpeechSynthesis()
  })

  afterEach(() => {
    delete globalThis.window
  })

  it('reports supported when SpeechSynthesis is present', () => {
    const provider = createBrowserTtsProvider()
    expect(provider.isSupported).toBe(true)
  })

  it('reports unsupported and calls onError when SpeechSynthesis is absent', () => {
    delete globalThis.window
    globalThis.window = {}
    const provider = createBrowserTtsProvider()
    const onError = vi.fn()

    expect(provider.isSupported).toBe(false)
    provider.speak('hello', { onError })

    expect(onError).toHaveBeenCalledWith(expect.objectContaining({ code: 'unsupported', recoverable: false }))
    expect(fakeSynthesis.speak).not.toHaveBeenCalled()
  })

  it('calls onStart when the utterance actually starts', () => {
    const provider = createBrowserTtsProvider()
    const onStart = vi.fn()
    provider.speak('hello', { onStart })

    const utterance = fakeSynthesis.speak.mock.calls[0][0]
    utterance.onstart()

    expect(onStart).toHaveBeenCalledOnce()
  })

  it('calls onNaturalEnd (never onStopped) when the utterance finishes on its own', () => {
    const provider = createBrowserTtsProvider()
    const onNaturalEnd = vi.fn()
    const onStopped = vi.fn()
    provider.speak('hello', { onNaturalEnd, onStopped })

    const utterance = fakeSynthesis.speak.mock.calls[0][0]
    utterance.onend()

    expect(onNaturalEnd).toHaveBeenCalledOnce()
    expect(onStopped).not.toHaveBeenCalled()
  })

  it('calls onStopped (never onNaturalEnd or onError) when the utterance is cancelled', () => {
    const provider = createBrowserTtsProvider()
    const onNaturalEnd = vi.fn()
    const onStopped = vi.fn()
    const onError = vi.fn()
    provider.speak('hello', { onNaturalEnd, onStopped, onError })

    const utterance = fakeSynthesis.speak.mock.calls[0][0]
    utterance.onerror({ error: 'canceled' })

    expect(onStopped).toHaveBeenCalledOnce()
    expect(onNaturalEnd).not.toHaveBeenCalled()
    expect(onError).not.toHaveBeenCalled()
  })

  it('calls onError with a normalized shape for a genuine synthesis failure', () => {
    const provider = createBrowserTtsProvider()
    const onError = vi.fn()
    const onStopped = vi.fn()
    provider.speak('hello', { onError, onStopped })

    const utterance = fakeSynthesis.speak.mock.calls[0][0]
    utterance.onerror({ error: 'synthesis-failed' })

    expect(onError).toHaveBeenCalledWith(
      expect.objectContaining({ code: 'synthesis-failed', recoverable: true, message: expect.any(String) }),
    )
    expect(onStopped).not.toHaveBeenCalled()
  })

  it('stop() calls the underlying cancel()', () => {
    const provider = createBrowserTtsProvider()
    provider.speak('hello')
    provider.stop()

    expect(fakeSynthesis.cancel).toHaveBeenCalled()
  })

  it('a stale (superseded) utterance never fires callbacks for the attempt that replaced it', () => {
    const provider = createBrowserTtsProvider()
    const firstCallbacks = { onNaturalEnd: vi.fn(), onStart: vi.fn() }
    provider.speak('first', firstCallbacks)
    const firstUtterance = fakeSynthesis.speak.mock.calls[0][0]

    const secondCallbacks = { onNaturalEnd: vi.fn() }
    provider.speak('second', secondCallbacks) // internally cancels the first

    // The first utterance's events arriving late must be inert.
    firstUtterance.onstart()
    firstUtterance.onend()

    expect(firstCallbacks.onStart).not.toHaveBeenCalled()
    expect(firstCallbacks.onNaturalEnd).not.toHaveBeenCalled()

    const secondUtterance = fakeSynthesis.speak.mock.calls[1][0]
    secondUtterance.onend()
    expect(secondCallbacks.onNaturalEnd).toHaveBeenCalledOnce()
  })
})
