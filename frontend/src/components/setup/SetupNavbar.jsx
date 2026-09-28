import { Moon, Sun } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useTheme } from '../../hooks/useTheme.js'
import BrandLogo from '../ui/BrandLogo.jsx'

// Deliberately minimal: the reference shows a full marketing nav (Home /
// Practice / Interview / Analytics / Resources), but this app only has one
// generic destination to link to from here — the landing page itself.
// "Practice"/"Analytics"/"Resources" have no real pages, so they're left
// out entirely rather than becoming dead links (see App.jsx's router).
// The theme toggle IS real (see hooks/useTheme.js) — everything else here
// is a genuine destination or control.
function SetupNavbar() {
  const { theme, toggleTheme } = useTheme()

  return (
    <header className="px-4 pt-3 sm:px-6 lg:px-10">
      <div className="flex h-11 items-center justify-between gap-3">
        <Link to="/" className="flex shrink-0 items-center">
          <BrandLogo />
        </Link>

        <div className="flex items-center gap-2">
          <Link
            to="/"
            className="rounded-full px-3.5 py-1.5 text-sm font-medium text-ink/70 transition-colors duration-200 hover:bg-glass/60 hover:text-ink"
          >
            Home
          </Link>
          <button
            type="button"
            onClick={toggleTheme}
            aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-glass/70 bg-glass/60 text-ink/70 transition-colors duration-200 hover:bg-glass hover:text-ink"
          >
            {theme === 'dark' ? <Sun className="h-4 w-4" strokeWidth={1.75} /> : <Moon className="h-4 w-4" strokeWidth={1.75} />}
          </button>
        </div>
      </div>
    </header>
  )
}

export default SetupNavbar
