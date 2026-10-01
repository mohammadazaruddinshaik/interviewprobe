import { useRef } from 'react'
import gsap from 'gsap'
import { useGSAP } from '@gsap/react'

gsap.registerPlugin(useGSAP)
gsap.config({ nullTargetWarn: false })

/**
 * One-time page entrance. The shell (`[data-shell]`) fades in, then every `[data-enter]` block rises into place in
 * document order. Only runs when the user has not asked for reduced motion; otherwise nothing is hidden or moved.
 */
export function usePageEntrance(ready = true) {
  const scope = useRef<HTMLDivElement>(null)
  useGSAP(
    () => {
      if (!ready) return
      const mm = gsap.matchMedia()
      mm.add('(prefers-reduced-motion: no-preference)', () => {
        gsap
          .timeline({ defaults: { ease: 'power3.out', clearProps: 'all' } })
          .from('[data-shell]', { autoAlpha: 0, duration: 0.35, clearProps: 'opacity,visibility' })
          .from('[data-enter]', { autoAlpha: 0, y: 16, duration: 0.6, stagger: 0.08 }, 0.1)
      })
    },
    { scope, dependencies: [ready] },
  )
  return scope
}
