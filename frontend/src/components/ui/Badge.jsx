// A small pill label — the hero eyebrow ("AI-Powered Interview Practice"),
// a feature tag, a numbered step marker. One shared recipe so every pill
// in the redesign matches, with `tone` covering the two shades actually
// used (a soft primary tint, and a plain neutral one for on-glass use).
const TONE_CLASSES = {
  primary: 'bg-primary-light text-primary',
  neutral: 'bg-white/70 text-muted',
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
