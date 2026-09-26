import { Link } from 'react-router-dom'
import { ArrowRightIcon } from './icons.jsx'

const VARIANT_CLASSES = {
  // The one solid, colored action per view — primary blue/indigo, soft
  // glow shadow, never the harsh flat "dark" button the old ink-on-cream
  // palette used.
  primary:
    'bg-primary text-white shadow-[0_8px_20px_-6px_rgba(91,111,245,0.55)] hover:bg-primary-2 focus-visible:outline-white',
  // A solid white pill for use on top of a colored/gradient surface (the
  // final CTA panel) — dark text reads clearly against the color behind it.
  inverse: 'bg-white text-ink shadow-glass-sm hover:bg-white/90',
  // The glass/ghost action — translucent surface, thin border, never
  // competes with primary.
  secondary:
    'border border-white/70 bg-white/60 text-ink backdrop-blur-sm hover:border-primary/30 hover:bg-white/80',
}

function Button({
  as,
  to,
  href,
  variant = 'primary',
  withArrow = false,
  className = '',
  children,
  ...props
}) {
  const base =
    'group inline-flex items-center justify-center gap-2 rounded-full px-6 py-3 text-sm font-medium transition-all duration-200 disabled:cursor-not-allowed disabled:pointer-events-none disabled:opacity-50'
  const classes = `${base} ${VARIANT_CLASSES[variant] ?? ''} ${className}`

  const content = (
    <>
      {children}
      {withArrow && (
        <ArrowRightIcon className="h-4 w-4 transition-transform duration-200 group-hover:translate-x-1" />
      )}
    </>
  )

  if (to) {
    return (
      <Link to={to} className={classes} {...props}>
        {content}
      </Link>
    )
  }

  if (as === 'a' || href) {
    return (
      <a href={href ?? '#'} className={classes} {...props}>
        {content}
      </a>
    )
  }

  return (
    <button type="button" className={classes} {...props}>
      {content}
    </button>
  )
}

export default Button
