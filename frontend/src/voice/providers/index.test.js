// Coverage for the provider factory's mode selection: InterviewProbe is
// voice-first via Deepgram (STT) and Azure Speech (TTS) only — there is no
// browser Web Speech API implementation to fall back to. `VITE_STT_MODE`/
// `VITE_TTS_MODE` must each be exactly "remote"; anything else must fail
// loudly rather than silently selecting some other implementation.
import { afterEach, describe, expect, it, vi } from 'vitest'

const { fakeRemoteStt, fakeRemoteTts, createRemoteSttProvider, createRemoteTtsProvider } = vi.hoisted(() => {
  const fakeRemoteStt = { isSupported: true, start: vi.fn(), stop: vi.fn(), dispose: vi.fn() }
  const fakeRemoteTts = { isSupported: true, speak: vi.fn(), stop: vi.fn(), dispose: vi.fn() }
  return {
    fakeRemoteStt,
    fakeRemoteTts,
    createRemoteSttProvider: vi.fn(() => fakeRemoteStt),
    createRemoteTtsProvider: vi.fn(() => fakeRemoteTts),
  }
})

vi.mock('./remoteSttProvider.js', () => ({ createRemoteSttProvider }))
vi.mock('./remoteTtsProvider.js', () => ({ createRemoteTtsProvider }))

afterEach(() => {
  vi.unstubAllEnvs()
  vi.clearAllMocks()
  vi.resetModules()
})

describe('createVoiceProviders', () => {
  it('1. selects the remote Deepgram STT provider when VITE_STT_MODE=remote', async () => {
    vi.stubEnv('VITE_STT_MODE', 'remote')
    vi.stubEnv('VITE_TTS_MODE', 'remote')
    const { createVoiceProviders } = await import('./index.js')

    const providers = createVoiceProviders()

    expect(createRemoteSttProvider).toHaveBeenCalledOnce()
    expect(providers.stt).toBe(fakeRemoteStt)
  })

  it('2. selects the remote Azure TTS provider when VITE_TTS_MODE=remote', async () => {
    vi.stubEnv('VITE_STT_MODE', 'remote')
    vi.stubEnv('VITE_TTS_MODE', 'remote')
    const { createVoiceProviders } = await import('./index.js')

    const providers = createVoiceProviders()

    expect(createRemoteTtsProvider).toHaveBeenCalledOnce()
    expect(providers.tts).toBe(fakeRemoteTts)
  })

  it('3. there is no browser fallback: an unset VITE_STT_MODE fails explicitly rather than selecting anything else', async () => {
    vi.stubEnv('VITE_STT_MODE', undefined)
    vi.stubEnv('VITE_TTS_MODE', 'remote')
    const { createVoiceProviders } = await import('./index.js')

    expect(() => createVoiceProviders()).toThrow(/VITE_STT_MODE/)
    expect(createRemoteSttProvider).not.toHaveBeenCalled()
  })

  it('4. there is no browser fallback: an unset VITE_TTS_MODE fails explicitly rather than selecting anything else', async () => {
    vi.stubEnv('VITE_STT_MODE', 'remote')
    vi.stubEnv('VITE_TTS_MODE', undefined)
    const { createVoiceProviders } = await import('./index.js')

    expect(() => createVoiceProviders()).toThrow(/VITE_TTS_MODE/)
    expect(createRemoteTtsProvider).not.toHaveBeenCalled()
  })

  it('5. a leftover "browser" mode value (the old default) is rejected, not silently honored', async () => {
    vi.stubEnv('VITE_STT_MODE', 'browser')
    vi.stubEnv('VITE_TTS_MODE', 'browser')
    const { createVoiceProviders } = await import('./index.js')

    // TTS is evaluated first (createVoiceProviders builds { tts, stt } in
    // that order) — either way, "browser" must never be silently honored.
    expect(() => createVoiceProviders()).toThrow(/VITE_TTS_MODE/)
    expect(createRemoteSttProvider).not.toHaveBeenCalled()
    expect(createRemoteTtsProvider).not.toHaveBeenCalled()
  })

  it('6. an unrecognized mode value fails explicitly rather than defaulting to anything', async () => {
    vi.stubEnv('VITE_STT_MODE', 'remote')
    vi.stubEnv('VITE_TTS_MODE', 'typo-of-remote')
    const { createVoiceProviders } = await import('./index.js')

    expect(() => createVoiceProviders()).toThrow(/VITE_TTS_MODE/)
  })
})
