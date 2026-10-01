import { useState } from 'react'
import type { ReactNode, Ref } from 'react'
import { Menu, X } from 'lucide-react'
import type { AuthUser } from '@/lib/auth'
import { APP_NAV } from '../lib/nav'
import AccountMenu from './AccountMenu'
import BrandMark from './BrandMark'

function NavList({ active, onNavigate }: { active: string; onNavigate: () => void }) {
  return (
    <ul className="flex flex-col gap-1">
      {APP_NAV.map(({ label, icon: Icon, href }) => {
        const current = label === active
        return (
          <li key={label}>
            <a
              href={href}
              aria-current={current ? 'page' : undefined}
              onClick={onNavigate}
              className={`relative flex h-11 items-center gap-3 rounded-lg px-3.5 text-[14px] font-medium outline-offset-2 transition-colors duration-200 focus-visible:outline-[3px] focus-visible:outline-yellow motion-reduce:transition-none ${
                current ? 'bg-yellow/30 text-ink' : 'text-ink/65 hover:bg-ink/[0.04] hover:text-ink'
              }`}
            >
              {current && <span aria-hidden="true" className="absolute left-0 top-2.5 h-6 w-[3px] rounded-r-full bg-orange" />}
              <Icon size={18} aria-hidden="true" className="shrink-0" />
              {label}
            </a>
          </li>
        )
      })}
    </ul>
  )
}

/**
 * The one authenticated shell for every cream page (dashboard, results, setup, result detail): a header with the
 * logo and the account control, a sidebar for the app's pages (a menu on small screens), and a constrained main area.
 * The interview room is deliberately outside it.
 */
function AppFrame({ user, active, rootRef, children }: { user: AuthUser | null; active: string; rootRef?: Ref<HTMLDivElement>; children: ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false)
  return (
    <div ref={rootRef} className="min-h-[100dvh] bg-cream text-ink">
      <header data-shell className="sticky top-0 z-30 border-b border-ink/10 bg-cream/90 backdrop-blur-sm">
        <div className="flex h-[68px] items-center justify-between gap-3 px-4 md:pr-8">
          <a href="/app" aria-label="InterviewProbe dashboard" className="inline-flex rounded-lg outline-offset-2 focus-visible:outline-[3px] focus-visible:outline-yellow">
            <BrandMark />
          </a>
          <div className="flex items-center gap-2">
            {user && <AccountMenu user={user} active={active} />}
            <button
              type="button"
              aria-expanded={menuOpen}
              aria-controls="app-mobile-menu"
              aria-label={menuOpen ? 'Close menu' : 'Open menu'}
              onClick={() => setMenuOpen((open) => !open)}
              className="inline-flex size-11 items-center justify-center rounded-lg border border-ink/15 text-ink outline-offset-2 focus-visible:outline-[3px] focus-visible:outline-yellow md:hidden"
            >
              {menuOpen ? <X size={20} aria-hidden="true" /> : <Menu size={20} aria-hidden="true" />}
            </button>
          </div>
        </div>
        {menuOpen && (
          <nav id="app-mobile-menu" aria-label="App" className="border-t border-ink/10 bg-cream p-3 md:hidden">
            <NavList active={active} onNavigate={() => setMenuOpen(false)} />
          </nav>
        )}
      </header>

      <div className="md:grid md:grid-cols-[232px_minmax(0,1fr)]">
        <aside data-shell className="sticky top-[68px] hidden h-[calc(100dvh-68px)] border-r border-ink/10 bg-[#faf9ee] px-4 py-5 md:block">
          <nav aria-label="App">
            <NavList active={active} onNavigate={() => undefined} />
          </nav>
        </aside>
        <main className="min-w-0">{children}</main>
      </div>
    </div>
  )
}

export default AppFrame
