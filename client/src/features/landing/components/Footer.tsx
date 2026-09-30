const FOOTER_COLUMNS = [
  {
    title: 'Product',
    links: [
      { label: 'Features', href: '#features' },
      { label: 'How It Works', href: '#how-it-works' },
      { label: 'Pricing', href: '#pricing' },
    ],
  },
  {
    title: 'Company',
    links: [
      { label: 'About', href: '#about' },
      { label: 'Contact', href: '#contact' },
      { label: 'Privacy Policy', href: '#privacy-policy' },
    ],
  },
  {
    title: 'Support',
    links: [
      { label: 'FAQ', href: '#faq' },
      { label: 'Terms of Service', href: '#terms-of-service' },
    ],
  },
]

const LEGAL_LINKS = [
  { label: 'Privacy', href: '#privacy' },
  { label: 'Terms', href: '#terms' },
  { label: 'Cookies', href: '#cookies' },
]

function Footer() {
  return (
    <footer data-anim="footer" className="px-4">
      <div className="mx-auto max-w-[1392px] border-t border-ink/20">
        <div className="mx-auto max-w-[1194px]">
          <div className="grid grid-cols-2 gap-x-6 gap-y-8 pb-8 pt-5 md:min-h-[147px] md:grid-cols-[1.6fr_1fr_1fr_1fr] xl:grid-cols-[537px_247px_244px_1fr] md:gap-x-0 md:gap-y-0 md:pb-0">
            <div className="col-span-2 md:col-span-1">
              <a href="#top" className="ml-[2px] inline-flex items-start gap-[13px]" aria-label="InterviewProbe home">
                <span className="relative block h-[40px] w-[40px] shrink-0 overflow-hidden">
                  <img
                    src="/assets/landing/logo.png"
                    alt=""
                    className="absolute -left-[32px] -top-[27px] h-[95px] w-[255px] max-w-none"
                  />
                </span>
                <span className="block">
                  <span className="mt-[3px] block text-base font-bold leading-[18px] tracking-[-0.01em] text-deep">
                    InterviewProbe
                  </span>
                  <span className="mt-[2px] block text-[10.5px] leading-[14px] text-ink/65">
                    Practice. Get Probed. Improve.
                  </span>
                </span>
              </a>
            </div>

            {FOOTER_COLUMNS.map((column) => (
              <nav key={column.title} aria-label={column.title} className="md:pt-[1px]">
                <h3 className="text-[11px] font-semibold leading-[14px] text-deep">{column.title}</h3>
                <ul className="mt-[6px] flex flex-col gap-[7px] text-[11.5px] leading-[14.3px]">
                  {column.links.map((link) => (
                    <li key={link.label}>
                      <a
                        href={link.href}
                        className="text-[11.5px] leading-[14.3px] text-ink/65 transition-colors hover:text-ink"
                      >
                        {link.label}
                      </a>
                    </li>
                  ))}
                </ul>
              </nav>
            ))}
          </div>

          <div className="border-t border-ink/15">
            <div className="flex flex-col gap-3 pb-6 pt-[8px] text-[11px] leading-[14px] text-ink/65 sm:flex-row sm:items-center sm:justify-between">
              <p>© 2026 InterviewProbe. All rights reserved.</p>
              <nav aria-label="Legal">
                <ul className="flex flex-wrap gap-x-[25px] gap-y-2">
                  {LEGAL_LINKS.map((link) => (
                    <li key={link.label}>
                      <a href={link.href} className="transition-colors hover:text-ink">
                        {link.label}
                      </a>
                    </li>
                  ))}
                </ul>
              </nav>
            </div>
          </div>
        </div>
      </div>
    </footer>
  )
}

export default Footer
