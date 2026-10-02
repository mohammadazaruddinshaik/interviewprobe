import { useRef } from 'react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { useGSAP } from '@gsap/react'

gsap.registerPlugin(useGSAP, ScrollTrigger)

const STEPS = [
  {
    number: '01',
    title: 'Choose your target',
    text: 'Set the role and interview focus.',
  },
  {
    number: '02',
    title: 'Build your plan',
    text: 'Get a role-specific interview path.',
  },
  {
    number: '03',
    title: 'Get probed',
    text: 'Answer naturally. Go deeper when needed.',
  },
  {
    number: '04',
    title: 'Review your performance',
    text: 'See what went well and what to improve.',
  },
]

function HowItWorksSection() {
  const scope = useRef<HTMLElement>(null)

  useGSAP(
    () => {
      const mm = gsap.matchMedia()

      mm.add('(prefers-reduced-motion: no-preference)', () => {
        const q = (name: string) => `[data-hiw="${name}"]`

        const tl = gsap.timeline({
          defaults: { ease: 'power2.out', clearProps: 'all' },
          scrollTrigger: { trigger: scope.current, start: 'top 70%', once: true },
        })

        tl.from(q('eyebrow'), { autoAlpha: 0, y: 12, duration: 0.5 })
          .from(q('headline'), { autoAlpha: 0, y: 22, duration: 0.65 }, 0.1)
          .from(q('image'), { autoAlpha: 0, y: 40, duration: 0.95 }, 0.2)

        gsap.utils.toArray<HTMLElement>(q('step')).forEach((step, i) => {
          const at = 0.35 + i * 0.16
          tl.from(step.querySelector(q('step-number')), { autoAlpha: 0, y: 10, duration: 0.4 }, at)
            .from(step.querySelector(q('step-title')), { autoAlpha: 0, y: 10, duration: 0.45 }, at + 0.08)
            .from(step.querySelector(q('step-text')), { autoAlpha: 0, y: 10, duration: 0.45 }, at + 0.16)
        })

        tl.from(q('line'), { scaleY: 0, transformOrigin: '50% 0%', duration: 0.9, ease: 'power1.inOut' }, 0.4)

        gsap.fromTo(
          q('parallax'),
          { yPercent: 2.5 },
          {
            yPercent: -2.5,
            ease: 'none',
            scrollTrigger: { trigger: scope.current, start: 'top bottom', end: 'bottom top', scrub: 0.6 },
          },
        )
      })
    },
    { scope },
  )

  return (
    <section
      ref={scope}
      id="how-it-works"
      aria-labelledby="how-it-works-heading"
      className="scroll-mt-16 overflow-x-clip px-4 pb-[88px] pt-[88px] md:pt-[104px]"
    >
      <div className="mx-auto grid max-w-[1054px] gap-14 lg:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)] lg:items-center lg:gap-x-10">
        <div>
          <p
            data-hiw="eyebrow"
            className="flex items-center gap-2.5 text-[11px] font-semibold tracking-[0.18em] text-ink/60"
          >
            <span aria-hidden="true" className="h-2 w-2 rounded-[2px] bg-yellow" />
            HOW IT WORKS
          </p>

          <h2
            id="how-it-works-heading"
            data-hiw="headline"
            className="mt-5 max-w-[480px] font-display text-[34px] font-extrabold leading-[1.08] tracking-[-0.02em] text-deep sm:text-[40px] lg:text-[42px] xl:text-[46px]"
          >
            From first question to <span className="whitespace-nowrap">interview-ready.</span>
          </h2>

          <ol className="relative mt-10 md:mt-12">
            <span
              aria-hidden="true"
              data-hiw="line"
              className="absolute bottom-6 left-[13px] top-6 w-px bg-forest/15"
            />
            {STEPS.map((step) => (
              <li key={step.number} data-hiw="step" className="group relative flex gap-5 py-4">
                <span
                  data-hiw="step-number"
                  className="relative z-10 flex h-[27px] w-[27px] shrink-0 items-center justify-center rounded-full bg-cream font-display text-[12px] font-extrabold text-forest/60 ring-1 ring-forest/20 transition-[background-color,color,box-shadow] duration-300 ease-out group-hover:bg-yellow group-hover:text-forest group-hover:ring-forest/40 motion-reduce:transition-none"
                >
                  {step.number}
                </span>
                <div>
                  <h3
                    data-hiw="step-title"
                    className="text-[16px] font-semibold text-deep transition-transform duration-300 ease-out group-hover:translate-x-[3px] motion-reduce:transition-none motion-reduce:group-hover:translate-x-0"
                  >
                    {step.title}
                  </h3>
                  <p
                    data-hiw="step-text"
                    className="mt-1 max-w-[380px] text-[14px] leading-[1.55] text-ink/60 transition-colors duration-300 ease-out group-hover:text-ink/85 motion-reduce:transition-none"
                  >
                    {step.text}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        </div>

        <div data-hiw="image">
          <div data-hiw="parallax">
            <div className="overflow-hidden rounded-[20px] shadow-[0_24px_48px_-28px_rgb(20_42_11/0.45)] md:rounded-[26px]">
              <img
                src="/assets/landing/how-it-works-1280.webp"
                srcSet="/assets/landing/how-it-works-640.webp 640w, /assets/landing/how-it-works-1280.webp 1280w"
                sizes="(max-width: 1023px) 92vw, 640px"
                alt="A candidate in a mock interview beside four floating cards: choose your target, get your interview plan, get probed, and understand your performance."
                width={1280}
                height={853}
                loading="lazy"
                decoding="async"
                className="h-auto w-full"
              />
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

export default HowItWorksSection
