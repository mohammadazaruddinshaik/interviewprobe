// A small glass chip: icon + title + one-line description. Used by the
// top-of-page feature strip and reused wherever a compact feature summary
// is needed, so every "quick glance" feature callout in the redesign shares
// one recipe.
function FeatureCard({ icon: Icon, title, description, className = '' }) {
  return (
    <div
      className={`flex items-start gap-3 rounded-2xl border border-white/70 bg-white/60 p-4 shadow-glass-sm backdrop-blur-xl ${className}`}
    >
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary-light text-primary">
        <Icon className="h-4.5 w-4.5" />
      </span>
      <div>
        <h3 className="text-sm font-semibold text-ink">{title}</h3>
        <p className="mt-0.5 text-xs leading-relaxed text-muted">{description}</p>
      </div>
    </div>
  )
}

export default FeatureCard
