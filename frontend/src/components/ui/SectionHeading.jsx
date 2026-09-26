import Badge from './Badge.jsx'

// The eyebrow + heading + supporting copy block every landing-page section
// opens with — centralized so heading size/spacing/hierarchy stays
// consistent across the feature/adaptive/voice/evaluation/role sections
// instead of each one redeclaring its own type scale.
function SectionHeading({ eyebrow, title, description, align = 'left', className = '' }) {
  const alignment = align === 'center' ? 'items-center text-center mx-auto' : 'items-start text-left'

  return (
    <div className={`flex max-w-2xl flex-col gap-4 ${alignment} ${className}`}>
      {eyebrow && <Badge>{eyebrow}</Badge>}
      <h2 className="text-3xl font-semibold leading-[1.15] tracking-tight text-ink sm:text-4xl">{title}</h2>
      {description && <p className="text-base leading-relaxed text-muted sm:text-lg">{description}</p>}
    </div>
  )
}

export default SectionHeading
