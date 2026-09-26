const PRODUCT_LINKS = [
  { label: 'Features', href: '#features' },
  { label: 'For Students', href: '#trust' },
  { label: 'Why Us', href: '#capabilities' },
]

const MORE_LINKS = [
  { label: 'GitHub', href: '#' },
  { label: 'Contact', href: '#' },
]

function Footer() {
  const year = new Date().getFullYear()

  return (
    <footer className="px-4 pb-4 sm:px-6">
      <div className="mx-auto max-w-6xl rounded-[24px] border border-white/70 bg-white/60 px-6 py-5 shadow-glass-sm backdrop-blur-xl sm:px-8">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2 text-ink">
            <img src="/assets/brand/logo-icon.svg" alt="" aria-hidden="true" className="h-5 w-5" />
            <span className="text-sm font-semibold tracking-tight">InterviewProbe</span>
          </div>

          <nav className="flex flex-wrap items-center gap-x-6 gap-y-2">
            {[...PRODUCT_LINKS, ...MORE_LINKS].map((link) => (
              <a
                key={link.label}
                href={link.href}
                className="text-sm text-ink/60 transition-colors duration-200 hover:text-ink"
              >
                {link.label}
              </a>
            ))}
          </nav>

          <p className="text-xs text-muted">© {year} InterviewProbe</p>
        </div>
      </div>
    </footer>
  )
}

export default Footer
