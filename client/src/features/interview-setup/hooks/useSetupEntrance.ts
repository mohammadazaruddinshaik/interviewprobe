import { useRef } from 'react'
import gsap from 'gsap'
import { useGSAP } from '@gsap/react'

gsap.registerPlugin(useGSAP)
gsap.config({ nullTargetWarn: false })

/** One-time, restrained entrance once the catalog has loaded (header, steps, summary). Skipped for reduced motion. */
export function useSetupEntrance(ready: boolean) {
  const scope = useRef<HTMLDivElement>(null)

  useGSAP(
    () => {
      if (!ready) return
      const mm = gsap.matchMedia()
      mm.add('(prefers-reduced-motion: no-preference)', () => {
        const q = (n: string) => `[data-setup="${n}"]`
        gsap
          .timeline({ defaults: { ease: 'power2.out', clearProps: 'all' } })
          .from(q('header'), { autoAlpha: 0, y: 12, duration: 0.45 })
          .from(q('step'), { autoAlpha: 0, y: 14, duration: 0.45, stagger: 0.08 }, 0.12)
          .from(q('summary'), { autoAlpha: 0, y: 14, duration: 0.5 }, 0.25)
      })
    },
    { scope, dependencies: [ready] },
  )

  return scope
}
