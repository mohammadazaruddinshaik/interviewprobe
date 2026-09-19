import { useState } from 'react'
import Button from '../ui/Button.jsx'
import { BrandMark, CloseIcon, MenuIcon } from '../ui/icons.jsx'

const NAV_LINKS = [
  { label: 'Product', href: '#product' },
  { label: 'How it works', href: '#how-it-works' },
  { label: 'Roles', href: '#roles' },
  { label: 'Resources', href: '#' },
]

function Navbar() {
  const [isMenuOpen, setIsMenuOpen] = useState(false)

  return (
    <header className="sticky top-0 z-50 border-b border-line/70 bg-cream/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
        <a href="#top" className="flex items-center gap-2 text-ink">
          <BrandMark className="h-6 w-6 text-accent" />
          <span className="text-base font-semibold tracking-tight">InterviewProbe</span>
        </a>

        <nav className="hidden items-center gap-8 md:flex">
          {NAV_LINKS.map((link) => (
            <a
              key={link.label}
              href={link.href}
              className="text-sm text-ink/70 transition-colors duration-200 hover:text-ink"
            >
              {link.label}
            </a>
          ))}
        </nav>

        <div className="hidden items-center gap-5 md:flex">
          <a
            href="#"
            className="text-sm font-medium text-ink/70 transition-colors duration-200 hover:text-ink"
          >
            Sign in
          </a>
          <Button to="/interview/new" variant="primary" withArrow className="px-5 py-2.5 text-sm">
            Get started
          </Button>
        </div>

        <button
          type="button"
          onClick={() => setIsMenuOpen((open) => !open)}
          aria-expanded={isMenuOpen}
          aria-controls="mobile-nav"
          aria-label={isMenuOpen ? 'Close menu' : 'Open menu'}
          className="flex h-9 w-9 items-center justify-center rounded-full text-ink transition-colors duration-200 hover:bg-accent-soft md:hidden"
        >
          {isMenuOpen ? <CloseIcon className="h-5 w-5" /> : <MenuIcon className="h-5 w-5" />}
        </button>
      </div>

      <div
        id="mobile-nav"
        className={`overflow-hidden border-t border-line/70 bg-cream transition-[max-height] duration-300 ease-in-out md:hidden ${
          isMenuOpen ? 'max-h-96' : 'max-h-0 border-t-0'
        }`}
      >
        <nav className="flex flex-col gap-1 px-6 py-4">
          {NAV_LINKS.map((link) => (
            <a
              key={link.label}
              href={link.href}
              onClick={() => setIsMenuOpen(false)}
              className="rounded-lg px-2 py-2.5 text-sm text-ink/80 transition-colors duration-200 hover:bg-accent-soft hover:text-ink"
            >
              {link.label}
            </a>
          ))}
          <div className="mt-2 flex flex-col gap-3 border-t border-line/70 pt-4">
            <a href="#" className="px-2 text-sm font-medium text-ink/70">
              Sign in
            </a>
            <Button to="/interview/new" variant="primary" withArrow className="justify-center">
              Get started
            </Button>
          </div>
        </nav>
      </div>
    </header>
  )
}

export default Navbar
