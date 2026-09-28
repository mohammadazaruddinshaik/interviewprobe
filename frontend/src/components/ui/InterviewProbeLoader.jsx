// InterviewProbe's own loading mark — three signal nodes on a single path,
// pulsing in sequence (thinking → deciding → continuing), never a generic
// spinner or sparkle. Used everywhere the product is briefly "thinking":
// interview startup, answer review, question preparation, result
// preparation. `label` is the one place contextual copy goes — this mark
// never appears bare with only "Loading…".
//
// `size`: "sm" sits inline next to a line of text (a busy button, a status
// row); "md" is the standalone moment (a whole panel's loading state).
const SIZES = {
  sm: { box: 20, r: 1.6 },
  md: { box: 34, r: 2.4 },
}

// `tone="current"` lets the mark sit inside an already-colored surface
// (e.g. the voice dock's solid-primary mic slot while reviewing an
// answer) and simply inherit that surface's text color instead of always
// asserting its own primary-blue, so it never fights the surface it's on.
function Mark({ size = 'md', tone = 'brand', className = '' }) {
  const { box, r } = SIZES[size] ?? SIZES.md
  const colorClass = tone === 'current' ? 'text-current' : 'text-primary'
  const nodes = [
    { cx: 6, cy: 15, delay: 0 },
    { cx: 12, cy: 6, delay: 0.22 },
    { cx: 18, cy: 15, delay: 0.44 },
  ]

  return (
    <svg viewBox="0 0 24 24" width={box} height={box} fill="none" aria-hidden="true" className={className}>
      <path
        d="M6 15L12 6L18 15"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeDasharray="24"
        className={`${colorClass} opacity-35 motion-safe:animate-probe-flow`}
      />
      {nodes.map(({ cx, cy, delay }) => (
        <circle
          key={cx + '-' + cy}
          cx={cx}
          cy={cy}
          r={r}
          fill="currentColor"
          className={`origin-center ${colorClass} motion-safe:animate-probe-pulse`}
          style={{ animationDelay: `${delay}s`, transformBox: 'fill-box' }}
        />
      ))}
    </svg>
  )
}

// The bare animated mark, for contexts that already provide their own
// label/status text nearby (e.g. VoiceStatusBar's mic slot during
// PROCESSING) and just need the glyph itself.
export function ProbeMark(props) {
  return <Mark {...props} />
}

// The standalone panel-level moment: mark + one line of contextual copy,
// stacked and centered. Deliberately compact — this is a brief pause in
// the interview, not a splash screen.
function InterviewProbeLoader({ label, size = 'md', className = '' }) {
  return (
    <div className={`flex flex-col items-center gap-3 text-center ${className}`}>
      <Mark size={size} />
      {label && (
        <p role="status" aria-live="polite" className="text-sm font-medium text-muted">
          {label}
        </p>
      )}
    </div>
  )
}

// The inline variant: mark + label on one line, for a busy button or a
// compact status row (e.g. "Reviewing your answer" in the voice dock).
export function InlineProbeLoader({ label, className = '' }) {
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <Mark size="sm" />
      {label && <span>{label}</span>}
    </span>
  )
}

export default InterviewProbeLoader
