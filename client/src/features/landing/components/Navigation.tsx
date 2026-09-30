import { useState } from 'react'
import { Menu, X } from 'lucide-react'

const NAV_LINKS = [
  { label: 'Features', href: '#features' },
  { label: 'How It Works', href: '#how-it-works' },
  { label: 'Pricing', href: '#pricing' },
]

const loginClass =
  'h-[35px] items-center justify-center rounded-lg border border-forest bg-cream px-[16px] text-[11px] font-semibold text-forest outline-offset-2 transition-colors duration-200 hover:bg-forest/[0.05] focus-visible:outline-2 focus-visible:outline-forest motion-reduce:transition-none'
const ctaClass =
  'h-[35px] items-center justify-center rounded-lg bg-forest px-[15px] text-[11px] font-semibold text-cream shadow-[inset_0_1px_0_rgb(255_255_255/0.12),0_1px_2px_rgb(20_42_11/0.3)] outline-offset-2 transition-[background-color,box-shadow,translate] duration-200 ease-out hover:-translate-y-px hover:bg-forest-light hover:shadow-[inset_0_1px_0_rgb(255_255_255/0.16),0_4px_10px_-4px_rgb(20_42_11/0.5)] focus-visible:outline-2 focus-visible:outline-forest active:translate-y-0 motion-reduce:transition-none motion-reduce:hover:translate-y-0'

function Navigation() {
  const [isMenuOpen, setIsMenuOpen] = useState(false)

  return (
    <header data-anim="nav" className="px-4 pt-[15px]">
      <nav
        aria-label="Primary"
        className="relative mx-auto max-w-[1036px] rounded-xl border border-dotted border-ink/30 bg-cream px-[15px]"
      >
        <div className="grid h-[52px] grid-cols-[1fr_auto] items-center md:grid-cols-[1fr_auto_1fr]">
          <a
            href="#top"
            className="relative block h-[38px] w-[196px] overflow-hidden"
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
                  className="text-[11px] font-medium text-ink transition-colors hover:text-forest"
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

        {isMenuOpen && (
          <div id="mobile-nav-menu" className="border-t border-dotted border-ink/30 pb-3 pt-3 md:hidden">
            <ul className="flex flex-col gap-1">
              {NAV_LINKS.map((link) => (
                <li key={link.href}>
                  <a
                    href={link.href}
                    className="block rounded-lg px-2 py-2 text-sm font-medium text-ink hover:bg-ink/5"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    {link.label}
                  </a>
                </li>
              ))}
              <li className="flex gap-3 pt-2">
                <a href="#login" className={`${loginClass} inline-flex flex-1`} onClick={() => setIsMenuOpen(false)}>
                  Log In
                </a>
                <a href="#start-practicing" className={`${ctaClass} inline-flex flex-[2]`} onClick={() => setIsMenuOpen(false)}>
                  Start Practicing Free
                </a>
              </li>
            </ul>
          </div>
        )}
      </nav>
    </header>
  )
}

export default Navigation
