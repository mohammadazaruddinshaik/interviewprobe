import { BrandMark } from '../ui/icons.jsx'

const PRODUCT_LINKS = [
  { label: 'Product', href: '#product' },
  { label: 'How it works', href: '#how-it-works' },
  { label: 'Roles', href: '#roles' },
]

const MORE_LINKS = [
  { label: 'GitHub', href: '#' },
  { label: 'Contact', href: '#' },
]

function Footer() {
  const year = new Date().getFullYear()

  return (
    <footer className="border-t border-line/70 bg-cream">
      <div className="mx-auto max-w-7xl px-6 py-14">
        <div className="grid gap-10 sm:grid-cols-3">
          <div className="flex items-center gap-2 text-ink">
            <BrandMark className="h-5 w-5 text-accent" />
            <span className="text-sm font-semibold tracking-tight">InterviewProbe</span>
          </div>

          <nav className="flex flex-col gap-2.5">
            {PRODUCT_LINKS.map((link) => (
              <a
                key={link.label}
                href={link.href}
                className="text-sm text-ink/60 transition-colors duration-200 hover:text-ink"
              >
                {link.label}
              </a>
            ))}
          </nav>

          <nav className="flex flex-col gap-2.5">
            {MORE_LINKS.map((link) => (
              <a
                key={link.label}
                href={link.href}
                className="text-sm text-ink/60 transition-colors duration-200 hover:text-ink"
              >
                {link.label}
              </a>
            ))}
          </nav>
        </div>

        <p className="mt-12 text-xs text-muted">© {year} InterviewProbe</p>
      </div>
    </footer>
  )
}

export default Footer
