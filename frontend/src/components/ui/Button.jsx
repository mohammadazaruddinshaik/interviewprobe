import { Link } from 'react-router-dom'
import { ArrowRightIcon } from './icons.jsx'

const VARIANT_CLASSES = {
  primary:
    'bg-ink text-cream hover:bg-ink/90 focus-visible:outline-cream',
  inverse:
    'bg-accent text-ink hover:bg-accent/90',
  secondary:
    'bg-white/70 text-ink border border-line hover:border-ink/30 hover:bg-white',
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
    'group inline-flex items-center justify-center gap-2 rounded-full px-6 py-3 text-sm font-medium transition-colors duration-200 disabled:cursor-not-allowed disabled:pointer-events-none disabled:opacity-50'
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
