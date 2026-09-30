import { useEffect, useRef, useState } from 'react'
import { Menu, X } from 'lucide-react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { useGSAP } from '@gsap/react'

gsap.registerPlugin(useGSAP, ScrollTrigger)

const NAV_LINKS = [
  { label: 'Features', href: '#features' },
  { label: 'How It Works', href: '#how-it-works' },
]

const loginClass =
  'h-[35px] items-center justify-center rounded-lg border border-forest bg-cream px-[16px] text-[11px] font-semibold text-forest outline-offset-2 transition-colors duration-200 hover:bg-forest/[0.05] focus-visible:outline-2 focus-visible:outline-forest motion-reduce:transition-none'
const ctaClass =
  'h-[35px] items-center justify-center rounded-lg bg-forest px-[15px] text-[11px] font-semibold text-cream shadow-[inset_0_1px_0_rgb(255_255_255/0.14),0_1px_2px_rgb(20_42_11/0.3),0_6px_12px_-6px_rgb(20_42_11/0.45)] outline-offset-2 transition-[background-color,box-shadow,translate] duration-200 ease-out hover:-translate-y-px hover:bg-forest-light hover:shadow-[inset_0_1px_0_rgb(255_255_255/0.18),0_2px_3px_rgb(20_42_11/0.3),0_8px_14px_-6px_rgb(20_42_11/0.55)] focus-visible:outline-2 focus-visible:outline-forest active:translate-y-0 motion-reduce:transition-none motion-reduce:hover:translate-y-0'

const linkClass =
  'relative inline-block rounded-sm py-1 text-[11px] font-medium text-ink outline-offset-4 transition-[color,translate] duration-200 ease-out after:absolute after:inset-x-0 after:bottom-0 after:h-px after:origin-left after:scale-x-0 after:bg-forest after:transition-transform after:duration-200 after:ease-out hover:-translate-y-px hover:text-forest hover:after:scale-x-100 focus-visible:outline-2 focus-visible:outline-forest aria-[current=true]:text-forest aria-[current=true]:after:scale-x-100 motion-reduce:transition-none motion-reduce:after:transition-none motion-reduce:hover:translate-y-0'

function Navigation() {
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const [activeId, setActiveId] = useState<string | null>(null)
  const headerRef = useRef<HTMLElement>(null)

  // Compact state: toggled via a data attribute, no per-frame React updates.
  useGSAP(() => {
    ScrollTrigger.create({
      start: 50,
      end: 'max',
      onToggle: (self) => {
        headerRef.current?.toggleAttribute('data-scrolled', self.isActive)
      },
    })
  })

  // Active section feedback.
  useEffect(() => {
    const targets = NAV_LINKS.map((link) => document.querySelector(link.href)).filter(
      (el): el is Element => el !== null,
    )
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) setActiveId(`#${entry.target.id}`)
          else setActiveId((current) => (current === `#${entry.target.id}` ? null : current))
        }
      },
      { rootMargin: '-35% 0px -55% 0px' },
    )
    targets.forEach((el) => observer.observe(el))
    return () => observer.disconnect()
  }, [])

  return (
    <>
    {/* Keeps the original in-flow height so the page below is not shifted by the fixed header. */}
    <div aria-hidden="true" className="h-[69px]" />
    <header
      ref={headerRef}
      data-anim="nav"
      className="group/nav fixed inset-x-0 top-0 z-50 px-4 pt-[15px] transition-[padding] duration-300 ease-out data-[scrolled]:pt-[10px] motion-reduce:transition-none"
    >
      <nav
        aria-label="Primary"
        className="relative mx-auto max-w-[1036px] rounded-xl border border-dotted border-ink/30 bg-cream px-[15px] transition-[border-color,box-shadow] duration-300 ease-out group-data-[scrolled]/nav:border-ink/45 group-data-[scrolled]/nav:shadow-[0_8px_20px_-12px_rgb(20_42_11/0.35)] motion-reduce:transition-none"
      >
        <div className="grid h-[52px] grid-cols-[1fr_auto] items-center transition-[height] duration-300 ease-out group-data-[scrolled]/nav:h-[46px] md:grid-cols-[1fr_auto_1fr] motion-reduce:transition-none">
          <a
            href="#top"
            className="relative block h-[38px] w-[196px] overflow-hidden rounded-sm outline-offset-4 transition-opacity duration-200 hover:opacity-75 focus-visible:outline-2 focus-visible:outline-forest motion-reduce:transition-none"
            aria-label="InterviewProbe home"
          >
            <img
              src="/assets/landing/logo.png"
              alt="InterviewProbe"
              className="absolute -left-[32px] -top-[27px] h-[95px] w-[255px] max-w-none"
            />
          </a>

          <ul className="hidden items-center gap-[35px] md:flex md:translate-x-[3px]">
            {NAV_LINKS.map((link) => (
              <li key={link.href}>
                <a
                  href={link.href}
                  aria-current={activeId === link.href ? 'true' : undefined}
                  className={linkClass}
                >
                  {link.label}
                </a>
              </li>
            ))}
          </ul>

          <div className="flex items-center justify-end gap-[13px]">
            <a href="#login" className={`${loginClass} hidden md:inline-flex`}>
              Log In
            </a>
            <a href="#start-practicing" className={`${ctaClass} hidden md:inline-flex`}>
              Start Practicing Free
            </a>

            <button
              type="button"
              className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-ink/20 text-ink transition-colors hover:bg-ink/5 md:hidden"
              aria-expanded={isMenuOpen}
              aria-controls="mobile-nav-menu"
              aria-label={isMenuOpen ? 'Close menu' : 'Open menu'}
              onClick={() => setIsMenuOpen((open) => !open)}
            >
              {isMenuOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
          </div>
        </div>

        <div
          id="mobile-nav-menu"
          aria-hidden={!isMenuOpen}
          className={`grid transition-[grid-template-rows,opacity,visibility] duration-300 ease-out motion-reduce:transition-none md:hidden ${
            isMenuOpen ? 'visible grid-rows-[1fr] opacity-100' : 'invisible grid-rows-[0fr] opacity-0'
          }`}
        >
          <div className="overflow-hidden">
            <ul className="flex flex-col gap-1 border-t border-dotted border-ink/30 pb-3 pt-3">
              {NAV_LINKS.map((link, i) => (
                <li
                  key={link.href}
                  style={{ transitionDelay: isMenuOpen ? `${60 + i * 50}ms` : '0ms' }}
                  className={`transition-[opacity,translate] duration-300 ease-out motion-reduce:transition-none ${
                    isMenuOpen ? 'translate-y-0 opacity-100' : '-translate-y-1 opacity-0'
                  }`}
                >
                  <a
                    href={link.href}
                    aria-current={activeId === link.href ? 'true' : undefined}
                    className="block rounded-lg px-2 py-3 text-sm font-medium text-ink transition-colors hover:bg-ink/5 aria-[current=true]:text-forest"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    {link.label}
                  </a>
                </li>
              ))}
              <li
                style={{ transitionDelay: isMenuOpen ? `${60 + NAV_LINKS.length * 50}ms` : '0ms' }}
                className={`flex gap-3 pt-2 transition-[opacity,translate] duration-300 ease-out motion-reduce:transition-none ${
                  isMenuOpen ? 'translate-y-0 opacity-100' : '-translate-y-1 opacity-0'
                }`}
              >
                <a href="#login" className={`${loginClass} inline-flex flex-1`} onClick={() => setIsMenuOpen(false)}>
                  Log In
                </a>
                <a href="#start-practicing" className={`${ctaClass} inline-flex flex-[2]`} onClick={() => setIsMenuOpen(false)}>
                  Start Practicing Free
                </a>
              </li>
            </ul>
          </div>
        </div>
      </nav>
    </header>
    </>
  )
}

export default Navigation
