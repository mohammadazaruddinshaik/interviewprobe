import { Menu, Moon, Sun, X } from 'lucide-react'
import { useState } from 'react'
import { useTheme } from '../../hooks/useTheme.js'
import Button from '../ui/Button.jsx'

// Only real, working destinations: "Home" and "Features" are same-page
// anchors, "Why Us" points at the capability grid further down. There is
// no pricing page, no docs, and no auth system, so none of those are
// shown — a visible control that does nothing is worse than one that
// doesn't exist. The theme toggle IS real (see hooks/useTheme.js).
const NAV_LINKS = [
  { label: 'Home', href: '#top' },
  { label: 'Features', href: '#features' },
  { label: 'Why Us', href: '#capabilities' },
]

function LandingNavbar() {
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const { theme, toggleTheme } = useTheme()

  return (
    <header className="relative px-4 pt-4 sm:px-6 sm:pt-5 lg:px-10 lg:pt-5">
      <div className="flex h-14 items-center justify-between gap-3">
        <a href="#top" className="flex shrink-0 items-center">
          <img src="/assets/brand/logo.svg" alt="InterviewProbe" className="h-7 w-auto sm:h-8" />
        </a>

        <nav className="hidden items-center gap-0.5 whitespace-nowrap rounded-full border border-glass/60 bg-glass/50 p-1 lg:flex">
          {NAV_LINKS.map((link) => (
            <a
              key={link.label}
              href={link.href}
              aria-current={link.label === 'Home' ? 'page' : undefined}
              className={`rounded-full px-3.5 py-2 text-sm font-medium transition-colors duration-200 ${
                link.label === 'Home'
                  ? 'bg-glass text-primary shadow-glass-sm'
                  : 'text-ink/70 hover:bg-glass/70 hover:text-ink'
              }`}
            >
              {link.label}
            </a>
          ))}
        </nav>

        <div className="hidden shrink-0 items-center gap-2 lg:flex">
          <button
            type="button"
            onClick={toggleTheme}
            aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-glass/70 bg-glass/60 text-ink/70 transition-colors duration-200 hover:bg-glass hover:text-ink"
          >
            {theme === 'dark' ? <Sun className="h-4.5 w-4.5" strokeWidth={1.75} /> : <Moon className="h-4.5 w-4.5" strokeWidth={1.75} />}
          </button>
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
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-glass/70 bg-glass/60 text-ink transition-colors duration-200 hover:bg-glass lg:hidden"
        >
          {isMenuOpen ? <X className="h-5 w-5" strokeWidth={1.75} /> : <Menu className="h-5 w-5" strokeWidth={1.75} />}
        </button>
      </div>

      <div
        id="landing-mobile-nav"
        className={`overflow-hidden transition-[max-height] duration-300 ease-in-out lg:hidden ${
          isMenuOpen ? 'max-h-[24rem]' : 'max-h-0'
        }`}
      >
        <nav className="mt-3 flex flex-col gap-1 rounded-2xl border border-glass/70 bg-glass/70 p-3">
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
          <button
            type="button"
            onClick={toggleTheme}
            className="flex items-center gap-2 rounded-xl px-3 py-2.5 text-left text-sm font-medium text-ink/80 transition-colors duration-200 hover:bg-primary-light/60 hover:text-ink"
          >
            {theme === 'dark' ? <Sun className="h-4 w-4" strokeWidth={1.75} /> : <Moon className="h-4 w-4" strokeWidth={1.75} />}
            {theme === 'dark' ? 'Light theme' : 'Dark theme'}
          </button>
          <div className="mt-1 border-t border-line pt-3">
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
