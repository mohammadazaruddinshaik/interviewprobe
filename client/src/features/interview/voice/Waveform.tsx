import { useEffect, useRef } from 'react'
import type { LevelMeter } from './audioLevel'

interface WaveformProps {
  /** Reads the live meter (TTS output or microphone). When absent, a calm hairline is drawn: no fake audio. */
  meter: () => LevelMeter | null
  active: boolean
  /** Interviewer audio is drawn in cream, the candidate's own voice in the accent yellow. */
  tone: 'ai' | 'you'
  className?: string
}

const BARS = 32
const HALF = BARS / 2

/** A symmetric voice envelope from real analyser data. A quiet hairline when inactive or under reduced motion. */
function Waveform({ meter, active, tone, className = '' }: WaveformProps) {
  const ref = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = ref.current
    const ctx = canvas?.getContext('2d')
    if (!canvas || !ctx) return
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const data = new Uint8Array(HALF)
    let frame = 0

    const draw = () => {
      const ratio = window.devicePixelRatio || 1
      const { clientWidth: w, clientHeight: h } = canvas
      if (canvas.width !== w * ratio || canvas.height !== h * ratio) {
        canvas.width = w * ratio
        canvas.height = h * ratio
      }
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0)
      ctx.clearRect(0, 0, w, h)
      const live = active && !reduced ? meter() : null
      if (live) live.bars(data)
      const color = tone === 'you' ? '253,228,90' : '253,253,245'
      // A quiet hairline is always the baseline; with real audio the envelope grows out of it.
      ctx.fillStyle = `rgba(${color},0.28)`
      ctx.beginPath()
      ctx.roundRect(w * 0.12, h / 2 - 0.75, w * 0.76, 1.5, 1)
      ctx.fill()
      if (!live) return
      const gap = 3
      const barW = (w - gap * (BARS - 1)) / BARS
      for (let i = 0; i < BARS; i += 1) {
        const k = Math.floor(Math.abs(i - (HALF - 0.5))) // 0 at the centre, HALF-1 at the edges
        const level = (data[k] ?? 0) / 255
        const barH = level * (1 - (k / HALF) * 0.55) * h
        if (barH < 3) continue
        ctx.fillStyle = `rgba(${color},${0.55 + level * 0.45})`
        ctx.beginPath()
        ctx.roundRect(i * (barW + gap), (h - barH) / 2, barW, barH, barW / 2)
        ctx.fill()
      }
      frame = requestAnimationFrame(draw)
    }
    draw()
    return () => cancelAnimationFrame(frame)
  }, [active, meter, tone])

  return <canvas ref={ref} aria-hidden="true" className={`block h-11 w-[176px] sm:w-[220px] ${className}`} />
}

export default Waveform
