import { useRef } from 'react'
import gsap from 'gsap'
import { useGSAP } from '@gsap/react'

gsap.registerPlugin(useGSAP)
gsap.config({ nullTargetWarn: false })

/** Restrained staggered entrance once the result is ready; skipped entirely for reduced motion. */
export function useResultEntrance(ready: boolean) {
  const scope = useRef<HTMLDivElement>(null)
  useGSAP(
    () => {
      if (!ready) return
      const mm = gsap.matchMedia()
      mm.add('(prefers-reduced-motion: no-preference)', () => {
        const q = (n: string) => `[data-result="${n}"]`
        gsap
          .timeline({ defaults: { ease: 'power2.out', clearProps: 'all' } })
          .from(q('header'), { autoAlpha: 0, y: 12, duration: 0.45 })
          .from(q('overall'), { autoAlpha: 0, y: 14, duration: 0.5 }, 0.1)
          .from([q('dimensions'), q('feedback'), q('evidence'), q('topics'), q('review')], { autoAlpha: 0, y: 14, duration: 0.45, stagger: 0.07 }, 0.2)
          .from(q('rail'), { autoAlpha: 0, y: 14, duration: 0.5 }, 0.3)
      })
    },
    { scope, dependencies: [ready] },
  )
  return scope
}
