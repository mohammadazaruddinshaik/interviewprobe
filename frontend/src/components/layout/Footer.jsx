import { ArrowUpRight } from 'lucide-react'
import BrandLogo from '../ui/BrandLogo.jsx'

// Only destinations that exist: the three sections on this page and the
// real repository (it matches this project's git origin). No Pricing,
// Docs, Contact, Terms, Privacy or social links, because none of those
// exist yet.
const LINKS = [
  { label: 'Home', href: '#top' },
  { label: 'Features', href: '#features' },
  { label: 'Why InterviewProbe', href: '#why' },
]

const REPOSITORY_URL = 'https://github.com/mohammadazaruddinshaik/interviewprobe'

// GitHub's own mark (lucide no longer ships brand glyphs).
function GitHubMark({ className }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" className={className}>
      <path d="M12 2C6.48 2 2 6.58 2 12.23c0 4.52 2.87 8.35 6.84 9.7.5.1.68-.22.68-.49l-.01-1.7c-2.78.62-3.37-1.36-3.37-1.36-.45-1.18-1.11-1.49-1.11-1.49-.91-.64.07-.63.07-.63 1 .07 1.53 1.06 1.53 1.06.9 1.57 2.35 1.12 2.92.85.09-.66.35-1.12.64-1.37-2.22-.26-4.56-1.14-4.56-5.07 0-1.12.39-2.04 1.03-2.76-.1-.26-.45-1.3.1-2.71 0 0 .84-.28 2.75 1.05A9.36 9.36 0 0 1 12 6.84c.85 0 1.71.12 2.51.34 1.91-1.33 2.75-1.05 2.75-1.05.55 1.41.2 2.45.1 2.71.64.72 1.03 1.64 1.03 2.76 0 3.94-2.34 4.81-4.57 5.06.36.32.68.94.68 1.9l-.01 2.81c0 .27.18.6.69.49A10.23 10.23 0 0 0 22 12.23C22 6.58 17.52 2 12 2z" />
    </svg>
  )
}

function Footer() {
  const year = new Date().getFullYear()

  return (
    <footer className="px-4 pb-5 sm:px-6 lg:px-10">
      <div className="mx-auto max-w-[1280px] rounded-[var(--radius-panel)] border border-glass/70 bg-glass/60 px-6 py-6 shadow-glass-sm backdrop-blur-xl sm:px-8">
        <div className="grid grid-cols-1 items-center gap-6 md:grid-cols-[1fr_auto_1fr]">
          <div>
            <BrandLogo />
            <p className="mt-2 text-sm text-muted">AI-powered technical interview practice.</p>
          </div>

          <nav aria-label="Footer" className="flex flex-wrap items-center gap-x-7 gap-y-2 md:justify-center">
            {LINKS.map((link) => (
              <a
                key={link.label}
                href={link.href}
                className="text-sm font-medium text-ink/70 transition-colors duration-200 hover:text-ink"
              >
                {link.label}
              </a>
            ))}
          </nav>

          <a
            href={REPOSITORY_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 justify-self-start text-sm font-medium text-ink/80 transition-colors duration-200 hover:text-ink md:justify-self-end"
          >
            <GitHubMark className="h-5 w-5" />
            GitHub
            <ArrowUpRight className="h-4 w-4 text-muted" strokeWidth={1.75} />
          </a>
        </div>

        <div className="mt-6 border-t border-line pt-5">
          <p className="text-xs text-muted">© {year} InterviewProbe</p>
        </div>
      </div>
    </footer>
  )
}

export default Footer
