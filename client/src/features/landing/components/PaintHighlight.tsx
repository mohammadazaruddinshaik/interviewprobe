import type { ReactNode } from 'react'

// Ragged-edged sweep mask: opaque on the left, organic edge, transparent on the right.
// Sized at 300% of the paint layer and slid left -> right via --paint-x (100 -> 0).
const PAINT_SWEEP_MASK = `url("data:image/svg+xml,${encodeURIComponent(
  "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 300 100' preserveAspectRatio='none'><path d='M0 0H150L158 8L151 19L161 31L153 44L163 56L154 69L162 81L152 92L157 100H0Z'/></svg>",
)}")`

const paintStyle = {
  '--paint-x': 0,
  WebkitMaskImage: PAINT_SWEEP_MASK,
  maskImage: PAINT_SWEEP_MASK,
  WebkitMaskSize: '300% 100%',
  maskSize: '300% 100%',
  WebkitMaskRepeat: 'no-repeat',
  maskRepeat: 'no-repeat',
  WebkitMaskPosition: 'calc(var(--paint-x) * 1%) 0',
  maskPosition: 'calc(var(--paint-x) * 1%) 0',
} as React.CSSProperties

interface PaintHighlightProps {
  anim: string
  className?: string
  children: ReactNode
}

/**
 * Yellow brush-stroke behind its children. The paint layer is absolutely positioned,
 * clipped to the wrapper and stacked behind the text, so it cannot leak or shift layout.
 * Fully painted by default; GSAP drives --paint-x on [data-anim="anim"] for the sweep.
 */
function PaintHighlight({ anim, className = '', children }: PaintHighlightProps) {
  return (
    <span className={`relative isolate inline-block text-deep ${className}`}>
      <span
        data-anim={anim}
        aria-hidden="true"
        style={paintStyle}
        className="pointer-events-none absolute inset-0 -z-10 overflow-hidden"
      >
        <svg viewBox="0 0 100 40" preserveAspectRatio="none" className="block h-full w-full fill-yellow">
          <path d="M3 9C10 6 22 8 35 6.5S60 8 75 6S92 7.5 98 9.5L99.5 14C98.5 20 99.5 26 98 31C90 34 78 32.5 62 34.5S30 33 14 35C8 35.5 4 33.5 2 30C1 24 2.5 15 3 9Z" />
        </svg>
      </span>
      {children}
    </span>
  )
}

export default PaintHighlight
