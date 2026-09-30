import { useRef } from 'react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { useGSAP } from '@gsap/react'

gsap.registerPlugin(useGSAP, ScrollTrigger)

const CLEAR = 'all'

export function useLandingAnimations<T extends HTMLElement>() {
  const scope = useRef<T>(null)

  useGSAP(
    () => {
      const mm = gsap.matchMedia()

      mm.add('(prefers-reduced-motion: no-preference)', () => {
        const el = (name: string) => `[data-anim="${name}"]`

        // Hero paint starts unrevealed and is swept in after the headline appears.
        gsap.set(el('hero-paint'), { '--paint-x': 100 })

        const tl = gsap.timeline({ defaults: { ease: 'power2.out', clearProps: CLEAR } })
        tl.from(el('nav'), { autoAlpha: 0, y: -12, duration: 0.45 })
          .from(el('hero-badge'), { autoAlpha: 0, y: 12, duration: 0.4 }, 0.15)
          .from(el('hero-title'), { autoAlpha: 0, y: 22, duration: 0.55 }, 0.25)
          .to(el('hero-paint'), { '--paint-x': 0, duration: 0.9, ease: 'power3.inOut', clearProps: 'none' }, 0.75)
          .from(el('hero-text'), { autoAlpha: 0, y: 14, duration: 0.45 }, 0.4)
          .from(el('hero-cta'), { autoAlpha: 0, y: 14, duration: 0.45 }, 0.5)
          .from(el('hero-trust'), { autoAlpha: 0, y: 8, duration: 0.4 }, 0.6)
          .from(
            el('hero-image'),
            { autoAlpha: 0, y: 24, scale: 0.985, duration: 0.7, transformOrigin: '50% 0%' },
            0.65,
          )
          .from(
            el('hero-paper'),
            { autoAlpha: 0, duration: 0.8, stagger: 0.1, clearProps: 'all' },
            0.6,
          )
      })
    },
    { scope },
  )

  return scope
}
