import { useRef } from 'react'
import gsap from 'gsap'
import { useGSAP } from '@gsap/react'

gsap.registerPlugin(useGSAP)
// Error/unauthenticated states render fewer sections than the full dashboard; missing targets are expected.
gsap.config({ nullTargetWarn: false })

/** Restrained one-time entrance: sidebar, greeting, next card, stats, recent, right rail. */
export function useDashboardEntrance() {
  const scope = useRef<HTMLDivElement>(null)

  useGSAP(
    () => {
      const mm = gsap.matchMedia()
      mm.add('(prefers-reduced-motion: no-preference)', () => {
        const q = (n: string) => `[data-dash="${n}"]`
        gsap
          .timeline({ defaults: { ease: 'power2.out', clearProps: 'all' } })
          .from(q('sidebar'), { autoAlpha: 0, x: -10, duration: 0.45 })
          .from(q('greeting'), { autoAlpha: 0, y: 14, duration: 0.5 }, 0.12)
          .from(q('next'), { autoAlpha: 0, y: 18, scale: 0.99, duration: 0.55 }, 0.24)
          .from(q('vis-q'), { autoAlpha: 0, y: 8, duration: 0.4 }, 0.55)
          .from(q('vis-a'), { autoAlpha: 0, y: 8, duration: 0.4 }, 0.8)
          .from(q('vis-p'), { autoAlpha: 0, y: 8, scale: 0.98, duration: 0.5 }, 1.05)
          .from(q('stats'), { autoAlpha: 0, y: 14, duration: 0.5 }, 0.36)
          .from(q('recent'), { autoAlpha: 0, y: 14, duration: 0.5 }, 0.46)
          .from(q('rail'), { autoAlpha: 0, y: 14, duration: 0.5, stagger: 0.08 }, 0.5)
      })
    },
    { scope },
  )

  return scope
}
