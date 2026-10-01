import { useEffect, useRef } from 'react'
import type { LevelMeter } from '../voice/audioLevel'

export type PresenceMode =
  | 'preparing'
  | 'speaking'
  | 'listening'
  | 'candidate'
  | 'finishing'
  | 'thinking'
  | 'completing'
  | 'error'

interface AiPresenceProps {
  mode: PresenceMode
  /** The live audio source for this mode: the interviewer's voice while speaking, the microphone for the candidate. */
  meter: () => LevelMeter | null
}

// How strongly the core follows REAL audio energy (0 = not at all). The candidate's response is deliberately subtler.
const AMPLITUDE: Partial<Record<PresenceMode, number>> = { speaking: 0.16, candidate: 0.1 }

const MOTION = 'ip-motion'

/**
 * An abstract presence on a dark stage. One restrained behaviour per mode:
 * preparing: a faint core, slowly warming · speaking: swells with the interviewer's real audio, soft rings
 * listening: a visible, breathing halo (your turn) · candidate: follows the candidate's real microphone level
 * finishing: gathers slightly · thinking: slow asymmetric light moving inside the core, no rotation
 * completing: dims · error: muted and still
 */
function AiPresence({ mode, meter }: AiPresenceProps) {
  const core = useRef<HTMLSpanElement>(null)
  const amplitude = AMPLITUDE[mode] ?? 0

  useEffect(() => {
    const el = core.current
    if (!el) return
    el.style.setProperty('--lvl', '0')
    if (!amplitude || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    let frame = 0
    const tick = () => {
      el.style.setProperty('--lvl', String(meter()?.level() ?? 0))
      frame = requestAnimationFrame(tick)
    }
    tick()
    return () => cancelAnimationFrame(frame)
  }, [amplitude, meter])

  const coreTone =
    mode === 'error'
      ? 'bg-[radial-gradient(circle_at_34%_28%,#c9cdb8_0%,#7d8872_40%,#3b4834_100%)] opacity-70'
      : 'bg-[radial-gradient(circle_at_34%_28%,#fde45a_0%,#7da23f_28%,#2c4d1f_62%,#10230a_100%)]'
  const coreMotion =
    mode === 'preparing'
      ? `${MOTION} animate-[ip-halo_3.6s_ease-in-out_infinite]`
      : mode === 'listening'
        ? `${MOTION} animate-[ip-breathe_5.5s_ease-in-out_infinite]`
        : mode === 'thinking'
          ? `${MOTION} animate-[ip-breathe_9s_ease-in-out_infinite]`
          : mode === 'finishing'
            ? 'scale-[0.95]'
            : mode === 'completing'
              ? 'opacity-60'
              : ''
  const glow = mode === 'error' ? '' : 'shadow-[0_0_90px_-12px_rgb(253_228_90/0.28),0_24px_60px_-20px_rgb(0_0_0/0.7)]'

  return (
    <div aria-hidden="true" className="relative grid size-[clamp(120px,24vh,272px)] place-items-center">
      {mode === 'speaking' && (
        <>
          <span className={`${MOTION} absolute inset-0 rounded-full border border-cream/25 animate-[ip-ring_3s_ease-out_infinite]`} />
          <span className={`${MOTION} absolute inset-0 rounded-full border border-cream/20 animate-[ip-ring_3s_ease-out_1.5s_infinite]`} />
        </>
      )}
      {(mode === 'listening' || mode === 'candidate') && (
        <span
          className={`${MOTION} absolute inset-[6%] rounded-full border ${
            mode === 'candidate' ? 'border-yellow/70' : 'border-yellow/55 animate-[ip-halo_4.5s_ease-in-out_infinite]'
          } shadow-[0_0_34px_rgb(253_228_90/0.18)]`}
        />
      )}
      {mode === 'thinking' && (
        <span className={`${MOTION} absolute inset-[4%] rounded-full bg-[radial-gradient(circle,rgb(253_228_90/0.16),transparent_70%)] animate-[ip-halo_6s_ease-in-out_infinite]`} />
      )}
      <span className="absolute inset-[10%] rounded-full bg-[radial-gradient(circle,rgb(253_228_90/0.14),transparent_68%)]" />
      <span
        ref={core}
        style={{ ['--lvl' as string]: 0, ['--amp' as string]: amplitude }}
        className={`relative block size-[64%] overflow-hidden rounded-full transition-[transform,opacity] duration-700 ease-out [transform:scale(calc(1+var(--lvl)*var(--amp)))] motion-reduce:transition-none ${glow} ${coreTone} ${coreMotion}`}
      >
        {mode === 'thinking' && (
          <span className={`${MOTION} absolute -inset-[10%] rounded-full bg-[radial-gradient(circle_at_50%_50%,rgb(253_228_90/0.42),transparent_46%)] animate-[ip-wander_13s_ease-in-out_infinite]`} />
        )}
      </span>
    </div>
  )
}

export default AiPresence
