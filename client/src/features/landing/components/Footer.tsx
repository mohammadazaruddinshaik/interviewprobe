import { useRef } from 'react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { useGSAP } from '@gsap/react'
import { ArrowRight, ArrowUpRight } from 'lucide-react'

gsap.registerPlugin(useGSAP, ScrollTrigger)

const GITHUB_URL = 'https://github.com/mohammadazaruddinshaik'

const FOOTER_COLUMNS = [
  {
    title: 'Product',
    links: [
      { label: 'Features', href: '#features' },
      { label: 'How It Works', href: '#how-it-works' },
    ],
  },
]

// Ragged-edged sweep mask: opaque on the left, organic edge, transparent on the right.
// Sized at 300% of the paint layer and slid left -> right via --paint-x (100 -> 0).
const PAINT_SWEEP_MASK = `url("data:image/svg+xml,${encodeURIComponent(
  "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 300 100' preserveAspectRatio='none'><path d='M0 0H150L158 8L151 19L161 31L153 44L163 56L154 69L162 81L152 92L157 100H0Z'/></svg>",
)}")`

const paintStyle = {
  '--paint-x': 0,
  WebkitMaskImage: PAINT_SWEEP_MASK,
  maskImage: PAINT_SWEEP_MASK,
  WebkitMaskSize: '300% 100%',
  maskSize: '300% 100%',
  WebkitMaskRepeat: 'no-repeat',
  maskRepeat: 'no-repeat',
  WebkitMaskPosition: 'calc(var(--paint-x) * 1%) 0',
  maskPosition: 'calc(var(--paint-x) * 1%) 0',
} as React.CSSProperties

const linkClass =
  'rounded-sm text-[14px] leading-[20px] text-ink/65 outline-offset-4 transition-colors duration-200 hover:text-deep focus-visible:outline-2 focus-visible:outline-forest motion-reduce:transition-none'

function GithubMark({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
    </svg>
  )
}

function Footer() {
  const scope = useRef<HTMLElement>(null)

  useGSAP(
    () => {
      const mm = gsap.matchMedia()

      mm.add('(prefers-reduced-motion: no-preference)', () => {
        const q = (name: string) => `[data-ft="${name}"]`

        // Paint starts unrevealed; the tween below sweeps it in left -> right.
        gsap.set(q('paint'), { '--paint-x': 100 })

        gsap
          .timeline({
            defaults: { ease: 'power2.out', clearProps: 'all' },
            scrollTrigger: { trigger: scope.current, start: 'top 80%', once: true },
          })
          .from(q('title'), { autoAlpha: 0, y: 24, duration: 0.7 })
          .to(q('paint'), { '--paint-x': 0, duration: 0.9, ease: 'power3.inOut', clearProps: 'none' }, 0.55)
          .from(q('text'), { autoAlpha: 0, y: 14, duration: 0.5 }, 0.15)
          .from(q('cta'), { autoAlpha: 0, y: 12, duration: 0.5 }, 0.3)
          .from(q('group'), { autoAlpha: 0, y: 14, duration: 0.5, stagger: 0.1 }, 0.4)
          .from(q('wordmark'), { autoAlpha: 0, y: 30, duration: 0.9 }, 0.5)
          .from(q('bottom'), { autoAlpha: 0, duration: 0.6 }, 0.8)
      })
    },
    { scope },
  )

  return (
    <footer ref={scope} className="overflow-x-clip px-4 pt-[72px] md:pt-[112px]">
      <div className="mx-auto max-w-[1194px]">
        {/* Closing CTA */}
        <div className="flex flex-col items-start gap-8 md:items-center md:text-center">
          <h2
            data-ft="title"
            className="max-w-[760px] font-display text-[38px] font-extrabold leading-[1.05] tracking-[-0.025em] text-deep sm:text-[52px] lg:text-[68px]"
          >
            Your next interview starts{' '}
            <span className="relative isolate inline-block px-[0.12em] text-deep">
              <span
                data-ft="paint"
                aria-hidden="true"
                style={paintStyle}
                className="pointer-events-none absolute inset-0 -z-10 overflow-hidden"
              >
                <svg viewBox="0 0 100 40" preserveAspectRatio="none" className="block h-full w-full fill-yellow">
                  <path d="M3 9C10 6 22 8 35 6.5S60 8 75 6S92 7.5 98 9.5L99.5 14C98.5 20 99.5 26 98 31C90 34 78 32.5 62 34.5S30 33 14 35C8 35.5 4 33.5 2 30C1 24 2.5 15 3 9Z" />
                </svg>
              </span>
              here.
            </span>
          </h2>
          <p data-ft="text" className="-mt-2 font-serif text-[18px] text-ink/70 sm:text-[20px]">
            Practice. Get probed. Improve.
          </p>
          <a
            data-ft="cta"
            href="#start-practicing"
            className="group inline-flex h-[60px] w-full items-center justify-center gap-3 rounded-[14px] bg-forest px-9 text-[17px] font-semibold tracking-[-0.005em] text-cream shadow-[inset_0_1px_0_rgb(255_255_255/0.14),0_1px_2px_rgb(20_42_11/0.3),0_12px_24px_-10px_rgb(20_42_11/0.55)] outline-offset-4 transition-[background-color,box-shadow,translate] duration-200 ease-out hover:-translate-y-0.5 hover:bg-forest-light hover:shadow-[inset_0_1px_0_rgb(255_255_255/0.18),0_2px_4px_rgb(20_42_11/0.3),0_18px_28px_-10px_rgb(20_42_11/0.6)] focus-visible:outline-[3px] focus-visible:outline-yellow active:translate-y-0 motion-reduce:transition-none motion-reduce:hover:translate-y-0 sm:w-auto"
          >
            Start Practicing Free
            <ArrowRight
              size={20}
              aria-hidden="true"
              className="transition-transform duration-200 ease-out group-hover:translate-x-1 motion-reduce:transition-none motion-reduce:group-hover:translate-x-0"
            />
          </a>
        </div>

        {/* Brand + navigation */}
        <div className="mt-[72px] grid grid-cols-2 gap-x-6 gap-y-10 border-t border-ink/15 pt-12 md:mt-[104px] md:grid-cols-[1.5fr_1fr] md:pt-14">
          <div data-ft="group" className="col-span-2 md:col-span-1">
            <a href="#top" className="inline-flex items-center gap-[13px]" aria-label="InterviewProbe home">
              <span className="relative block h-[40px] w-[40px] shrink-0 overflow-hidden">
                <img
                  src="/assets/landing/logo.png"
                  alt=""
                  className="absolute -left-[32px] -top-[27px] h-[95px] w-[255px] max-w-none"
                />
              </span>
              <span className="text-[22px] font-extrabold tracking-[-0.02em] text-deep">InterviewProbe</span>
            </a>
            <p className="mt-4 max-w-[300px] font-serif text-[16px] leading-[1.45] text-ink/70">
              AI-powered interview practice that adapts to you.
            </p>
            <a
              href={GITHUB_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="group mt-6 inline-flex items-center gap-3 rounded-full border border-forest/25 bg-cream py-2 pl-2 pr-4 text-deep outline-offset-4 transition-[border-color,background-color] duration-200 hover:border-forest/60 hover:bg-forest/[0.04] focus-visible:outline-2 focus-visible:outline-forest motion-reduce:transition-none"
            >
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-forest text-cream">
                <GithubMark size={18} />
              </span>
              <span className="leading-tight">
                <span className="block text-[11px] text-ink/60">Built by Azaruddin</span>
                <span className="flex items-center gap-1 text-[14px] font-semibold">
                  GitHub
                  <ArrowUpRight
                    size={14}
                    aria-hidden="true"
                    className="transition-transform duration-200 group-hover:-translate-y-px group-hover:translate-x-px motion-reduce:transition-none"
                  />
                </span>
              </span>
            </a>
          </div>

          {FOOTER_COLUMNS.map((column) => (
            <nav key={column.title} data-ft="group" aria-label={column.title}>
              <h3 className="text-[11px] font-semibold tracking-[0.18em] text-ink/50">
                {column.title.toUpperCase()}
              </h3>
              <ul className="mt-5 flex flex-col gap-3">
                {column.links.map((link) => (
                  <li key={link.label}>
                    <a href={link.href} className={linkClass}>
                      {link.label}
                    </a>
                  </li>
                ))}
              </ul>
            </nav>
          ))}
        </div>

        {/* Wordmark */}
        <div
          data-ft="wordmark"
          aria-hidden="true"
          className="mt-14 select-none text-center font-display text-[10.5vw] font-extrabold leading-[0.9] tracking-[-0.04em] text-forest/[0.07] md:mt-20 md:text-[min(10.5vw,150px)]"
        >
          InterviewProbe
        </div>

        {/* Bottom bar */}
        <div data-ft="bottom" className="mt-8 border-t border-ink/15">
          <div className="flex flex-col gap-4 pb-8 pt-6 text-[13px] text-ink/60 md:flex-row md:items-center md:justify-between">
            <p>© 2026 InterviewProbe</p>
            <ul className="flex flex-wrap items-center gap-x-6 gap-y-3">
              <li>
                <a
                  href={GITHUB_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 rounded-sm outline-offset-4 transition-colors duration-200 hover:text-deep focus-visible:outline-2 focus-visible:outline-forest motion-reduce:transition-none"
                >
                  <GithubMark size={14} />
                  GitHub
                </a>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </footer>
  )
}

export default Footer
