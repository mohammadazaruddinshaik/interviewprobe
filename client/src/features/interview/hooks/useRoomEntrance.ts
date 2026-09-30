import { useRef } from 'react'
import gsap from 'gsap'
import { useGSAP } from '@gsap/react'

gsap.registerPlugin(useGSAP)
gsap.config({ nullTargetWarn: false })

/** Restrained entrance when the room becomes ready, plus a short fade when the question changes. */
export function useRoomEntrance(phase: string, questionId: string | null) {
  const scope = useRef<HTMLDivElement>(null)

  useGSAP(
    () => {
      const mm = gsap.matchMedia()
      mm.add('(prefers-reduced-motion: no-preference)', () => {
        const q = (n: string) => `[data-room="${n}"]`
        if (phase === 'ready') {
          gsap
            .timeline({ defaults: { ease: 'power2.out', clearProps: 'all' } })
            .from(q('header'), { autoAlpha: 0, y: 10, duration: 0.4 })
            .from(q('question'), { autoAlpha: 0, y: 14, duration: 0.5 }, 0.1)
            .from(q('composer'), { autoAlpha: 0, y: 14, duration: 0.5 }, 0.2)
            .from(q('rail'), { autoAlpha: 0, y: 14, duration: 0.5 }, 0.3)
        } else if (phase === 'completed') {
          gsap.from(q('completed'), { autoAlpha: 0, y: 14, duration: 0.5, ease: 'power2.out', clearProps: 'all' })
        }
      })
    },
    { scope, dependencies: [phase] },
  )

  useGSAP(
    () => {
      if (!questionId) return
      const mm = gsap.matchMedia()
      mm.add('(prefers-reduced-motion: no-preference)', () => {
        gsap.from('[data-room="question-text"]', { autoAlpha: 0, y: 8, duration: 0.35, ease: 'power2.out', clearProps: 'all' })
      })
    },
    { scope, dependencies: [questionId], revertOnUpdate: false },
  )

  return scope
}
