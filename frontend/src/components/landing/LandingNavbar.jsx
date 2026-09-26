import { Menu, Sun, X } from 'lucide-react'
import { useState } from 'react'
import Button from '../ui/Button.jsx'

// "Pricing"/"Docs" have no real destination anywhere in the app yet — left
// as inert placeholders (the same treatment "Sign in" already gets, since
// there's no auth system either) rather than inventing a fake page.
// "For Students"/"Why Us" point at the two same-page sections that most
// closely answer those questions (the trust strip and the capability
// grid), since no dedicated pages exist for them.
const NAV_LINKS = [
  { label: 'Home', href: '#top' },
  { label: 'Features', href: '#features' },
  { label: 'For Students', href: '#trust' },
  { label: 'Why Us', href: '#capabilities' },
  { label: 'Pricing', href: '#' },
  { label: 'Docs', href: '#' },
]

function LandingNavbar() {
  const [isMenuOpen, setIsMenuOpen] = useState(false)

  return (
    <header className="relative px-4 pt-4 sm:px-6 sm:pt-5 lg:px-10 lg:pt-5">
      <div className="flex h-14 items-center justify-between gap-3">
        <a href="#top" className="flex shrink-0 items-center">
          <img src="/assets/brand/logo.svg" alt="InterviewProbe" className="h-7 w-auto sm:h-8" />
        </a>

        <nav className="hidden items-center gap-0.5 whitespace-nowrap rounded-full border border-white/60 bg-white/50 p-1 xl:flex">
          {NAV_LINKS.map((link) => (
            <a
              key={link.label}
              href={link.href}
              aria-current={link.label === 'Home' ? 'page' : undefined}
              className={`rounded-full px-3 py-2 text-sm font-medium transition-colors duration-200 ${
                link.label === 'Home'
                  ? 'bg-white text-primary shadow-glass-sm'
                  : 'text-ink/70 hover:bg-white/70 hover:text-ink'
              }`}
            >
              {link.label}
            </a>
          ))}
        </nav>

        <div className="hidden shrink-0 items-center gap-2 whitespace-nowrap xl:flex">
          <button
            type="button"
            aria-label="Toggle theme"
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-white/70 bg-white/60 text-ink/70 transition-colors duration-200 hover:bg-white"
          >
            <Sun className="h-4.5 w-4.5" strokeWidth={1.75} />
          </button>
          <a
            href="#"
            className="rounded-full border border-white/70 bg-white/60 px-4 py-2 text-sm font-medium text-ink transition-colors duration-200 hover:bg-white"
          >
            Sign in
          </a>
          <Button to="/interview/new" variant="primary" withArrow className="px-5 py-2.5 text-sm">
            Get Started
          </Button>
        </div>

        <button
          type="button"
          onClick={() => setIsMenuOpen((open) => !open)}
          aria-expanded={isMenuOpen}
          aria-controls="landing-mobile-nav"
          aria-label={isMenuOpen ? 'Close menu' : 'Open menu'}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-white/70 bg-white/60 text-ink transition-colors duration-200 hover:bg-white xl:hidden"
        >
          {isMenuOpen ? <X className="h-5 w-5" strokeWidth={1.75} /> : <Menu className="h-5 w-5" strokeWidth={1.75} />}
        </button>
      </div>

      <div
        id="landing-mobile-nav"
        className={`overflow-hidden transition-[max-height] duration-300 ease-in-out xl:hidden ${
          isMenuOpen ? 'max-h-[26rem]' : 'max-h-0'
        }`}
      >
        <nav className="mt-3 flex flex-col gap-1 rounded-2xl border border-white/70 bg-white/70 p-3">
          {NAV_LINKS.map((link) => (
            <a
              key={link.label}
              href={link.href}
              onClick={() => setIsMenuOpen(false)}
              className="rounded-xl px-3 py-2.5 text-sm font-medium text-ink/80 transition-colors duration-200 hover:bg-primary-light/60 hover:text-ink"
            >
              {link.label}
            </a>
          ))}
          <div className="mt-1 flex flex-col gap-2 border-t border-line pt-3">
            <a href="#" className="px-3 text-sm font-medium text-ink/70">
              Sign in
            </a>
            <Button to="/interview/new" variant="primary" withArrow className="justify-center">
              Get Started
            </Button>
          </div>
        </nav>
      </div>
    </header>
  )
}

export default LandingNavbar
