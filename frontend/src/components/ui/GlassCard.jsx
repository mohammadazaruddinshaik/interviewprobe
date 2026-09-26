// The one reusable glass surface every marketing panel is built from:
// translucent white, a thin light border, a soft low-opacity shadow, and a
// large rounded corner. Kept as a single component so every surface in the
// redesign shares exactly the same recipe rather than each section
// re-deriving its own opacity/blur/shadow values.
//
// `as` lets a caller render a <section>/<article>/etc. instead of a <div>
// without duplicating the visual recipe.
function GlassCard({ as: Tag = 'div', className = '', children, ...props }) {
  return (
    <Tag
      className={`rounded-[28px] border border-white/70 bg-white/60 shadow-glass backdrop-blur-xl ${className}`}
      {...props}
    >
      {children}
    </Tag>
  )
}

export default GlassCard
