/** A tiny wrapper over an AnalyserNode: real audio energy for the presence orb and waveform (no fake data). */
export interface LevelMeter {
  /** Overall loudness, 0..1. */
  level: () => number
  /** Fills `out` with 0..255 frequency magnitudes. */
  bars: (out: Uint8Array) => void
  close: () => void
}

type AudioContextCtor = typeof AudioContext

function contextCtor(): AudioContextCtor | null {
  const w = window as unknown as { AudioContext?: AudioContextCtor; webkitAudioContext?: AudioContextCtor }
  return w.AudioContext ?? w.webkitAudioContext ?? null
}

export function createLevelMeter(source: MediaStream | HTMLMediaElement): LevelMeter | null {
  const Ctor = contextCtor()
  if (!Ctor) return null
  // Routing a media element through Web Audio makes it silent if the context cannot start. A context only starts
  // freely after a user gesture, so without one we skip the meter and let the audio play untouched.
  if (!(source instanceof MediaStream) && !navigator.userActivation?.hasBeenActive) return null
  try {
    const context = new Ctor()
    const analyser = context.createAnalyser()
    analyser.fftSize = 256
    analyser.smoothingTimeConstant = 0.75
    const node = source instanceof MediaStream ? context.createMediaStreamSource(source) : context.createMediaElementSource(source)
    node.connect(analyser)
    // A media element must stay audible; a microphone stream must NOT be routed to the speakers.
    if (!(source instanceof MediaStream)) analyser.connect(context.destination)
    void context.resume().catch(() => undefined)
    const data = new Uint8Array(analyser.frequencyBinCount)
    return {
      level: () => {
        analyser.getByteFrequencyData(data)
        let sum = 0
        for (let i = 0; i < data.length; i += 1) sum += data[i]
        return Math.min(1, sum / data.length / 110)
      },
      bars: (out) => {
        analyser.getByteFrequencyData(data)
        const step = Math.max(1, Math.floor((data.length * 0.75) / out.length))
        for (let i = 0; i < out.length; i += 1) out[i] = data[i * step] ?? 0
      },
      close: () => {
        try {
          node.disconnect()
          analyser.disconnect()
        } catch {
          /* already disconnected */
        }
        void context.close().catch(() => undefined)
      },
    }
  } catch {
    return null
  }
}
