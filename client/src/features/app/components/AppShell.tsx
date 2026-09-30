import { useState } from 'react'
import type { ReactNode, Ref } from 'react'

export type SidebarMode = 'rail' | 'menu'

interface AppShellProps {
  /** Renders the navigation. `rail` = persistent sidebar, `menu` = mobile dropdown. */
  sidebar: (mode: SidebarMode, close: () => void) => ReactNode
  topBar: (controls: { menuOpen: boolean; toggleMenu: () => void }) => ReactNode
  rootRef?: Ref<HTMLDivElement>
  children: ReactNode
}

/**
 * Reusable product shell: persistent sidebar (compact on tablet, full on wide desktop),
 * top bar, and a mobile dropdown menu instead of the sidebar on small screens.
 */
function AppShell({ sidebar, topBar, rootRef, children }: AppShellProps) {
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <div ref={rootRef} className="min-h-screen bg-cream text-ink md:grid md:grid-cols-[72px_minmax(0,1fr)] xl:grid-cols-[232px_minmax(0,1fr)]">
      <aside
        data-dash="sidebar"
        className="sticky top-0 hidden h-screen border-r border-ink/10 bg-cream md:block"
      >
        {sidebar('rail', () => undefined)}
      </aside>

      <div className="min-w-0">
        <header className="sticky top-0 z-30 border-b border-ink/10 bg-cream">
          {topBar({ menuOpen, toggleMenu: () => setMenuOpen((open) => !open) })}
          <div
            id="app-mobile-menu"
            aria-hidden={!menuOpen}
            className={`grid transition-[grid-template-rows,opacity,visibility] duration-300 ease-out motion-reduce:transition-none md:hidden ${
              menuOpen ? 'visible grid-rows-[1fr] opacity-100' : 'invisible grid-rows-[0fr] opacity-0'
            }`}
          >
            <div className="overflow-hidden border-t border-ink/10 bg-cream">
              {sidebar('menu', () => setMenuOpen(false))}
            </div>
          </div>
        </header>

        <main>{children}</main>
      </div>
    </div>
  )
}

export default AppShell
