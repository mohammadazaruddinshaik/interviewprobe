const SIZES = {
  // Score-breakdown dimension rings.
  md: { box: 112, stroke: 8, textClass: 'text-2xl' },
  // The single overall-score ring.
  lg: { box: 148, stroke: 9, textClass: 'text-4xl' },
}

// A circular score indicator built from two plain SVG circles (no chart
// library) — the same accessible contract this page has always exposed
// for its four score dimensions (`role="progressbar"` with the exact
// `"{label}: {score} out of 10"` name), now drawn as a ring instead of a
// horizontal bar. `color` is a CSS color value (a design-token var), never
// a raw hex chosen per instance.
function ScoreRing({ score, label, color, size = 'md', showLabel = true }) {
  const { box, stroke, textClass } = SIZES[size] ?? SIZES.md
  const radius = (box - stroke) / 2
  const circumference = 2 * Math.PI * radius
  const clamped = Math.max(0, Math.min(10, score))
  const offset = circumference * (1 - clamped / 10)
  const rounded = score.toFixed(1)

  return (
    <div className="flex flex-col items-center gap-1">
      <div
        role="progressbar"
        aria-valuenow={Number(rounded)}
        aria-valuemin={0}
        aria-valuemax={10}
        aria-label={`${label}: ${rounded} out of 10`}
        className="relative"
        style={{ width: box, height: box }}
      >
        <svg width={box} height={box} className="-rotate-90">
          <circle cx={box / 2} cy={box / 2} r={radius} fill="none" stroke="var(--color-line)" strokeWidth={stroke} />
          <circle
            cx={box / 2}
            cy={box / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className="transition-[stroke-dashoffset] duration-700 ease-out motion-reduce:transition-none"
          />
        </svg>
        <span
          aria-hidden="true"
          className={`absolute inset-0 flex items-center justify-center font-semibold tabular-nums text-ink ${textClass}`}
        >
          {rounded}
        </span>
      </div>
      {showLabel && <p className="text-center text-sm font-semibold text-ink">{label}</p>}
    </div>
  )
}

export default ScoreRing
