import { BrandMark } from '../ui/icons.jsx'

const PRODUCT_LINKS = [
  { label: 'Features', href: '#features' },
  { label: 'How It Works', href: '#how-it-works' },
  { label: 'Roles', href: '#roles' },
]

const MORE_LINKS = [
  { label: 'GitHub', href: '#' },
  { label: 'Contact', href: '#' },
]

function Footer() {
  const year = new Date().getFullYear()

  return (
    <footer className="px-4 pb-6 sm:px-6">
      <div className="mx-auto max-w-6xl rounded-[28px] border border-white/70 bg-white/60 px-6 py-12 shadow-glass-sm backdrop-blur-xl sm:px-10">
        <div className="grid gap-10 sm:grid-cols-3">
          <div className="flex items-center gap-2 text-ink">
            <BrandMark className="h-5 w-5 text-primary" />
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
