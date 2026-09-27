const PRODUCT_LINKS = [
  { label: 'Features', href: '#features' },
  { label: 'Why InterviewProbe', href: '#capabilities' },
]

// The real repository behind this app — no placeholder "#" links, and no
// "Contact" entry since there is no real contact destination yet.
const MORE_LINKS = [{ label: 'GitHub', href: 'https://github.com/mohammadazaruddinshaik/interviewprobe' }]

function Footer() {
  const year = new Date().getFullYear()

  return (
    <footer className="px-4 pb-4 sm:px-6">
      <div className="mx-auto max-w-6xl rounded-[24px] border border-glass/70 bg-glass/60 px-6 py-5 shadow-glass-sm backdrop-blur-xl sm:px-8">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2.5 text-ink">
            <img src="/assets/brand/logo-icon.svg" alt="" aria-hidden="true" className="h-5 w-5" />
            <div>
              <p className="text-sm font-semibold tracking-tight leading-tight">InterviewProbe</p>
              <p className="text-xs leading-tight text-muted">AI-powered technical interview practice.</p>
            </div>
          </div>

          <nav className="flex flex-wrap items-center gap-x-6 gap-y-2">
            {[...PRODUCT_LINKS, ...MORE_LINKS].map((link) => {
              const isExternal = link.href.startsWith('http')
              return (
                <a
                  key={link.label}
                  href={link.href}
                  {...(isExternal ? { target: '_blank', rel: 'noopener noreferrer' } : {})}
                  className="text-sm text-ink/60 transition-colors duration-200 hover:text-ink"
                >
                  {link.label}
                </a>
              )
            })}
          </nav>

          <p className="text-xs text-muted">© {year} InterviewProbe</p>
        </div>
      </div>
    </footer>
  )
}

export default Footer
