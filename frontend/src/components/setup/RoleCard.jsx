import { ChevronRight } from 'lucide-react'

// A row in the role list, not a card in a grid — deliberately avoiding the
// generic "blue outline + checkmark in a circle" selection pattern. The
// selected state instead reads through a left accent bar, a soft
// background tint, and the title/chevron shifting to the primary color —
// closer to a focused list control than a dashboard tile.
function RoleCard({ icon: Icon, label, description, selected, onClick, className = '' }) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onClick}
      className={`group relative flex w-full items-center gap-3 rounded-lg py-2 pl-4 pr-3 text-left transition-colors duration-150 ${
        selected ? 'bg-primary-light/35' : 'hover:bg-glass/60'
      } ${className}`}
    >
      <span
        aria-hidden="true"
        className={`absolute left-0 top-1/2 h-7 w-[3px] -translate-y-1/2 rounded-full bg-primary transition-opacity duration-150 ${
          selected ? 'opacity-100' : 'opacity-0'
        }`}
      />
      <span
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border transition-colors duration-150 ${
          selected ? 'border-primary/30 bg-glass text-primary' : 'border-line bg-glass/70 text-primary/80'
        }`}
      >
        <Icon className="h-4 w-4" strokeWidth={1.75} />
      </span>
      <span className="min-w-0 flex-1">
        {/* The role name always wraps rather than truncating, even at the
            narrowest widths — only the (already short) descriptor gives up
            space first, hidden below `sm` and truncated above it. */}
        <span className={`block text-sm font-semibold leading-snug ${selected ? 'text-primary' : 'text-ink'}`}>
          {label}
        </span>
        <span className="hidden truncate text-[11px] leading-tight text-muted sm:block">{description}</span>
      </span>
      <ChevronRight
        className={`h-4 w-4 shrink-0 transition-all duration-150 ${
          selected ? 'translate-x-0.5 text-primary' : 'text-muted/50 group-hover:text-muted'
        }`}
        strokeWidth={2}
      />
    </button>
  )
}

export default RoleCard
