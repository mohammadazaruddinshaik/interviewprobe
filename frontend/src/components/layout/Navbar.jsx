import { useState } from 'react'
import Button from '../ui/Button.jsx'
import { BrandMark, CloseIcon, MenuIcon } from '../ui/icons.jsx'

const NAV_LINKS = [
  { label: 'Home', href: '#top' },
  { label: 'Features', href: '#features' },
  { label: 'How It Works', href: '#how-it-works' },
  { label: 'Roles', href: '#roles' },
  { label: 'About', href: '#evaluation' },
]

// A floating, rounded glass bar (matches the reference: a pill-shaped panel
// with margin on every side, not a full-width sticky strip) — desktop keeps
// the logo left, nav centered, and actions right; mobile collapses to a
// logo + a single compact menu button so nothing can overflow the bar.
function Navbar() {
  const [isMenuOpen, setIsMenuOpen] = useState(false)

  return (
    <header className="sticky top-4 z-50 px-4 sm:top-6 sm:px-6">
      {/* A fixed radius (never rounded-full) so the bar stays a clean
          rounded rectangle once the mobile menu expands it — rounded-full
          on a much taller open state would stretch into an oval. */}
      <div className="mx-auto max-w-6xl rounded-[28px] border border-white/70 bg-white/70 shadow-glass-sm backdrop-blur-xl">
        <div className="flex h-16 items-center justify-between gap-4 px-4 sm:px-6">
          <a href="#top" className="flex shrink-0 items-center gap-2 text-ink">
            <BrandMark className="h-6 w-6 text-primary" />
            <span className="text-base font-semibold tracking-tight">InterviewProbe</span>
          </a>

          <nav className="hidden items-center gap-1 lg:flex">
            {NAV_LINKS.map((link) => (
              <a
                key={link.label}
                href={link.href}
                className="rounded-full px-4 py-2 text-sm font-medium text-ink/70 transition-colors duration-200 hover:bg-primary-light/60 hover:text-ink"
              >
                {link.label}
              </a>
            ))}
          </nav>

          <div className="hidden items-center gap-3 lg:flex">
            <a
              href="#"
              className="rounded-full px-4 py-2 text-sm font-medium text-ink/70 transition-colors duration-200 hover:text-ink"
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
            aria-controls="mobile-nav"
            aria-label={isMenuOpen ? 'Close menu' : 'Open menu'}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-ink transition-colors duration-200 hover:bg-primary-light/60 lg:hidden"
          >
            {isMenuOpen ? <CloseIcon className="h-5 w-5" /> : <MenuIcon className="h-5 w-5" />}
          </button>
        </div>

        <div
          id="mobile-nav"
          className={`overflow-hidden transition-[max-height] duration-300 ease-in-out lg:hidden ${
            isMenuOpen ? 'max-h-96 border-t border-white/70' : 'max-h-0'
          }`}
        >
          <nav className="flex flex-col gap-1 px-4 py-4">
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
            <div className="mt-2 flex flex-col gap-3 border-t border-line pt-4">
              <a href="#" className="px-3 text-sm font-medium text-ink/70">
                Sign in
              </a>
              <Button to="/interview/new" variant="primary" withArrow className="justify-center">
                Get Started
              </Button>
            </div>
          </nav>
        </div>
      </div>
    </header>
  )
}

export default Navbar
