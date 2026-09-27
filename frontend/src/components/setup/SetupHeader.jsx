import { ArrowLeft, Zap } from 'lucide-react'
import { Link } from 'react-router-dom'

// The AI badge here is purely descriptive copy — never a configuration
// control. The candidate never sees or sets difficulty/topics/model/
// provider anywhere on this page. Kept deliberately compact (single-line
// title + subtitle) so the header never eats into the no-scroll desktop
// budget.
function SetupHeader() {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div className="flex items-center gap-3">
        <Link
          to="/"
          aria-label="Back to home"
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-glass/70 bg-glass/60 text-ink transition-colors duration-200 hover:bg-glass"
        >
          <ArrowLeft className="h-4 w-4" strokeWidth={1.75} />
        </Link>

        <div>
          <h1 className="text-xl font-extrabold leading-tight tracking-tight text-ink sm:text-2xl">
            Create Your{' '}
            <span className="bg-gradient-to-r from-primary to-primary-2 bg-clip-text text-transparent">
              Interview
            </span>
          </h1>
          <p className="text-xs text-muted sm:text-sm">Choose a role and start a realistic technical interview.</p>
        </div>
      </div>

      <div className="flex items-center gap-2 rounded-xl border border-glass/70 bg-glass/60 px-3 py-1.5 shadow-glass-sm">
        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-primary-light text-primary">
          <Zap className="h-3.5 w-3.5" strokeWidth={1.75} />
        </span>
        <div>
          <p className="text-[11px] font-semibold leading-tight text-ink">AI-Powered</p>
          <p className="text-[11px] leading-tight text-muted">Adaptive &amp; Role-Specific</p>
        </div>
      </div>
    </div>
  )
}

export default SetupHeader
