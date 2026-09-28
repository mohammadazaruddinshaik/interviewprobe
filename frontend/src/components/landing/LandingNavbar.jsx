import { Menu, Moon, Sun, X } from 'lucide-react'
import { useState } from 'react'
import { useTheme } from '../../hooks/useTheme.js'
import BrandLogo from '../ui/BrandLogo.jsx'
import Button from '../ui/Button.jsx'

// Only real, working destinations: every link is a same-page anchor to a
// section that exists below. There is no pricing page, no docs, and no
// auth system, so none of those appear. The theme toggle is real
// (hooks/useTheme.js) and persists across every page.
const NAV_LINKS = [
  { label: 'Home', href: '#top' },
  { label: 'Features', href: '#features' },
  { label: 'Why InterviewProbe', href: '#why' },
]

function ThemeToggle({ theme, onToggle, className = '' }) {
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
      className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-glass/70 bg-glass/60 text-ink/70 transition-colors duration-200 hover:bg-glass hover:text-ink ${className}`}
    >
      {theme === 'dark' ? <Sun className="h-4.5 w-4.5" strokeWidth={1.75} /> : <Moon className="h-4.5 w-4.5" strokeWidth={1.75} />}
    </button>
  )
}

// A floating glass bar rather than a header row inside a page shell —
// the master reference's navigation sits on the open backdrop.
function LandingNavbar() {
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const { theme, toggleTheme } = useTheme()

  return (
    <header className="sticky top-3 z-30 px-3 pt-3 sm:px-6 sm:pt-4">
      <div className="mx-auto max-w-[1280px] rounded-[1.375rem] border border-glass/70 bg-glass/65 px-3 shadow-glass-sm backdrop-blur-xl sm:px-5">
        <div className="flex h-16 items-center justify-between gap-3">
          <a href="#top" className="flex shrink-0 items-center pl-1">
            <BrandLogo />
          </a>

          <nav aria-label="Primary" className="hidden items-center gap-1 lg:flex">
            {NAV_LINKS.map((link) => (
              <a
                key={link.label}
                href={link.href}
                aria-current={link.label === 'Home' ? 'page' : undefined}
                className={`rounded-full px-4 py-2 text-sm font-medium transition-colors duration-200 ${
                  link.label === 'Home'
                    ? 'bg-glass text-primary shadow-glass-sm'
                    : 'text-ink/70 hover:bg-glass/70 hover:text-ink'
                }`}
              >
                {link.label}
              </a>
            ))}
          </nav>

          <div className="hidden shrink-0 items-center gap-2.5 lg:flex">
            <ThemeToggle theme={theme} onToggle={toggleTheme} />
            <Button to="/interview/new" variant="primary" withArrow className="px-5 py-2.5">
              Get Started
            </Button>
          </div>

          <div className="flex items-center gap-2 lg:hidden">
            <ThemeToggle theme={theme} onToggle={toggleTheme} />
            <button
              type="button"
              onClick={() => setIsMenuOpen((open) => !open)}
              aria-expanded={isMenuOpen}
              aria-controls="landing-mobile-nav"
              aria-label={isMenuOpen ? 'Close menu' : 'Open menu'}
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-glass/70 bg-glass/60 text-ink transition-colors duration-200 hover:bg-glass"
            >
              {isMenuOpen ? <X className="h-5 w-5" strokeWidth={1.75} /> : <Menu className="h-5 w-5" strokeWidth={1.75} />}
            </button>
          </div>
        </div>

        <div
          id="landing-mobile-nav"
          className={`overflow-hidden transition-[max-height] duration-300 ease-in-out lg:hidden ${
            isMenuOpen ? 'max-h-80' : 'max-h-0'
          }`}
        >
          <nav aria-label="Mobile" className="flex flex-col gap-1 border-t border-line pb-3 pt-3">
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
            <Button to="/interview/new" variant="primary" withArrow className="mt-2 justify-center">
              Get Started
            </Button>
          </nav>
        </div>
      </div>
    </header>
  )
}

export default LandingNavbar
