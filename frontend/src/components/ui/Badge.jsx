// A small pill label — the hero eyebrow ("AI-Powered Interview Practice"),
// a feature tag, a numbered step marker. One shared recipe so every pill
// across the app matches, with `tone` covering the shades actually used.
const TONE_CLASSES = {
  primary: 'bg-primary-light text-primary',
  neutral: 'bg-glass/70 text-muted',
  // A translucent glass chip with a thin border — the hero eyebrow's
  // on-backdrop treatment, distinct from `primary`'s solid tint fill.
  glass: 'border border-glass/70 bg-glass/70 text-primary',
}

function Badge({ tone = 'primary', className = '', children }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs font-semibold ${TONE_CLASSES[tone] ?? TONE_CLASSES.primary} ${className}`}
    >
      {children}
    </span>
  )
}

export default Badge
