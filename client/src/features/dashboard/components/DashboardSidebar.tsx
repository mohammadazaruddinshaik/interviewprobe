import { FileText, LayoutGrid, MessagesSquare, Settings, TrendingUp } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import type { SidebarMode } from '@/features/app/components/AppShell'

interface NavItem {
  label: string
  icon: LucideIcon
  href: string
}

const MAIN_NAV: NavItem[] = [
  { label: 'Overview', icon: LayoutGrid, href: '/app' },
  { label: 'Interviews', icon: MessagesSquare, href: '#interviews' },
  { label: 'Performance', icon: TrendingUp, href: '#performance' },
  { label: 'Resume', icon: FileText, href: '#resume' },
]

const SETTINGS_NAV: NavItem = { label: 'Settings', icon: Settings, href: '#settings' }

const ACTIVE = 'Overview'

function NavLink({ item, mode, onNavigate }: { item: NavItem; mode: SidebarMode; onNavigate: () => void }) {
  const Icon = item.icon
  const active = item.label === ACTIVE
  const showLabel = mode === 'menu' ? '' : 'md:hidden xl:inline'
  return (
    <a
      href={item.href}
      aria-current={active ? 'page' : undefined}
      title={item.label}
      onClick={onNavigate}
      className={`group relative flex h-10 items-center gap-3 rounded-lg px-3 text-[14px] font-medium outline-offset-2 transition-colors duration-200 focus-visible:outline-2 focus-visible:outline-forest motion-reduce:transition-none ${
        mode === 'rail' ? 'md:justify-center xl:justify-start' : ''
      } ${active ? 'bg-forest/[0.07] text-deep' : 'text-ink/60 hover:bg-forest/[0.04] hover:text-deep'}`}
    >
      {active && <span aria-hidden="true" className="absolute left-0 top-2.5 h-5 w-[3px] rounded-full bg-yellow" />}
      <Icon size={18} strokeWidth={active ? 2.2 : 1.8} aria-hidden="true" className="shrink-0" />
      <span className={showLabel}>{item.label}</span>
    </a>
  )
}

function DashboardSidebar({ mode, close }: { mode: SidebarMode; close: () => void }) {
  return (
    <nav aria-label="App" className={`flex flex-col ${mode === 'rail' ? 'h-full p-3 xl:p-4' : 'p-3'}`}>
      {mode === 'rail' && (
        <a
          href="/"
          aria-label="InterviewProbe home"
          className="mb-6 flex h-[52px] items-center justify-center overflow-hidden xl:justify-start"
        >
          <span className="relative block h-[38px] w-[38px] shrink-0 overflow-hidden xl:hidden">
            <img src="/assets/landing/logo.png" alt="" className="absolute -left-[31px] -top-[26px] h-[95px] w-[255px] max-w-none" />
          </span>
          <span className="relative hidden h-[38px] w-[196px] overflow-hidden xl:block">
            <img src="/assets/landing/logo.png" alt="InterviewProbe" className="absolute -left-[32px] -top-[27px] h-[95px] w-[255px] max-w-none" />
          </span>
        </a>
      )}

      <ul className="flex flex-col gap-1">
        {MAIN_NAV.map((item) => (
          <li key={item.label}>
            <NavLink item={item} mode={mode} onNavigate={close} />
          </li>
        ))}
      </ul>

      <div className="mt-4 border-t border-ink/10 pt-4 md:mt-auto">
        <NavLink item={SETTINGS_NAV} mode={mode} onNavigate={close} />
      </div>
    </nav>
  )
}

export default DashboardSidebar
