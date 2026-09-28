import { Moon, Sun } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useTheme } from '../../hooks/useTheme.js'
import BrandLogo from '../ui/BrandLogo.jsx'

// Contextual section labels only — the reference shows a full marketing
// nav (Home / Practice / Interview / Results / Resources), but this app
// has no real "Practice" or "Resources" destination and no per-session
// "Interview" hub to link to once a session is complete (see App.jsx's
// router). Rendered as inert, muted labels rather than fake routes or
// dead links — the same resolution the Interview room's navbar already
// uses for its own non-existent sections. "Results" is the one real
// section this page belongs to, shown as the active item.
const INERT_LABELS = ['Practice', 'Interview', 'Resources']

function ResultsNavbar() {
  const { theme, toggleTheme } = useTheme()

  return (
    <header className="px-4 pt-3 sm:px-6 lg:px-8">
      <div className="flex h-12 items-center justify-between gap-3">
        <Link to="/" className="flex shrink-0 items-center">
          <BrandLogo />
        </Link>

        <nav
          aria-label="Product sections"
          className="hidden items-center gap-1 rounded-full border border-line bg-glass/50 p-1 lg:flex"
        >
          <Link
            to="/"
            className="rounded-full px-3.5 py-1.5 text-sm font-medium text-ink/70 transition-colors duration-200 hover:bg-glass/70 hover:text-ink"
          >
            Home
          </Link>
          <span
            aria-current="page"
            className="rounded-full bg-glass px-3.5 py-1.5 text-sm font-medium text-primary shadow-glass-sm"
          >
            Results
          </span>
          {INERT_LABELS.map((label) => (
            <span key={label} aria-disabled="true" className="cursor-default px-3.5 py-1.5 text-sm text-muted/70">
              {label}
            </span>
          ))}
        </nav>

        <button
          type="button"
          onClick={toggleTheme}
          aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-glass/70 bg-glass/60 text-ink/70 transition-colors duration-200 hover:bg-glass hover:text-ink"
        >
          {theme === 'dark' ? <Sun className="h-4 w-4" strokeWidth={1.75} /> : <Moon className="h-4 w-4" strokeWidth={1.75} />}
        </button>
      </div>
    </header>
  )
}

export default ResultsNavbar
