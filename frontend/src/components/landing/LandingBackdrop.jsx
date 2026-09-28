// The Landing page's ambient decoration: large soft arcs, dotted fields,
// and radial glows, drawn entirely in CSS/SVG (never a raster image) and
// always behind content. Every value routes through theme tokens, so the
// same shapes re-skin for dark mode instead of glowing white on navy.
// This layer clips its own oversized arcs (`overflow-hidden`); it contains
// no content, so nothing real can ever be clipped by it.
function DotField({ className }) {
  return (
    <div
      className={`absolute opacity-40 ${className}`}
      style={{
        backgroundImage: 'radial-gradient(var(--color-primary) 1.1px, transparent 1.2px)',
        backgroundSize: '16px 16px',
        maskImage: 'radial-gradient(closest-side, black, transparent)',
        WebkitMaskImage: 'radial-gradient(closest-side, black, transparent)',
      }}
    />
  )
}

function LandingBackdrop() {
  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
      {/* Soft radial light, top-left and right. */}
      <div className="absolute -left-40 -top-40 h-[34rem] w-[34rem] rounded-full bg-primary-light/60 blur-3xl" />
      <div className="absolute -right-32 top-24 h-[28rem] w-[28rem] rounded-full bg-tint-purple-light/60 blur-3xl" />
      <div className="absolute -left-24 top-[62%] h-[26rem] w-[26rem] rounded-full bg-primary-light/50 blur-3xl" />

      {/* Large organic arcs sweeping behind the hero and the lower page. */}
      <svg className="absolute left-1/2 top-0 h-[70rem] w-[120rem] -translate-x-1/2" viewBox="0 0 1920 1120" fill="none">
        <path
          d="M-80 360C260 120 620 40 980 120S1640 420 2000 300"
          stroke="var(--color-primary)"
          strokeOpacity="0.10"
          strokeWidth="1.5"
        />
        <path
          d="M-120 820C240 600 560 560 900 660S1560 960 2040 760"
          stroke="var(--color-accent-2)"
          strokeOpacity="0.10"
          strokeWidth="1.5"
        />
        <ellipse cx="1650" cy="160" rx="420" ry="420" fill="var(--color-glass)" fillOpacity="0.28" />
        <ellipse cx="160" cy="980" rx="520" ry="360" fill="var(--color-glass)" fillOpacity="0.22" />
      </svg>

      {/* Dotted fields, faded out at their edges. */}
      <DotField className="right-[4%] top-20 h-64 w-64" />
      <DotField className="left-[2%] top-[58%] h-56 w-56" />
      <DotField className="right-[10%] top-[70%] h-48 w-48" />

      {/* A few small floating points of light. */}
      <span className="absolute left-[3%] top-[22%] h-3 w-3 rounded-full bg-glass shadow-glass-sm" />
      <span className="absolute left-[6%] top-[30%] h-2 w-2 rounded-full bg-glass/80" />
      <span className="absolute right-[18%] top-[48%] h-2 w-2 rounded-full bg-primary/30" />
    </div>
  )
}

export default LandingBackdrop
