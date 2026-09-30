import { Bell, ChevronDown, Menu, X } from 'lucide-react'

interface DashboardTopBarProps {
  userName: string
  /** Breadcrumb text shown beside the brand; defaults to the dashboard's "Overview". */
  context?: string
  menuOpen: boolean
  toggleMenu: () => void
}

function DashboardTopBar({ userName, context = 'Overview', menuOpen, toggleMenu }: DashboardTopBarProps) {
  return (
    <div className="flex h-[54px] items-center md:h-[60px] justify-between px-4 md:px-6 lg:px-10">
      {/* Mobile: brand + menu. Wider screens show the brand in the sidebar. */}
      <div className="flex items-center gap-3">
        <a href="/" aria-label="InterviewProbe home" className="relative block h-[36px] w-[180px] overflow-hidden md:hidden">
          <img src="/assets/landing/logo.png" alt="InterviewProbe" className="absolute -left-[29px] -top-[25px] h-[87px] w-[234px] max-w-none" />
        </a>
        <p className="hidden text-[13px] font-medium text-ink/50 md:block">{context}</p>
      </div>

      <div className="flex items-center gap-1.5 sm:gap-3">
        <button
          type="button"
          aria-label="Notifications"
          className="relative inline-flex h-10 w-10 items-center justify-center rounded-lg text-ink/70 outline-offset-2 transition-colors duration-200 hover:bg-forest/[0.06] hover:text-deep focus-visible:outline-2 focus-visible:outline-forest motion-reduce:transition-none"
        >
          <Bell size={18} aria-hidden="true" />
          <span aria-hidden="true" className="absolute right-[11px] top-[11px] h-1.5 w-1.5 rounded-full bg-orange" />
        </button>

        <button
          type="button"
          className="hidden h-10 items-center gap-2.5 rounded-lg pl-1.5 pr-2 outline-offset-2 transition-colors duration-200 hover:bg-forest/[0.06] focus-visible:outline-2 focus-visible:outline-forest motion-reduce:transition-none sm:flex"
        >
          <span aria-hidden="true" className="flex h-7 w-7 items-center justify-center rounded-full bg-forest text-[11px] font-bold text-cream">
            {userName.charAt(0)}
          </span>
          <span className="text-[14px] font-medium text-deep">{userName}</span>
          <ChevronDown size={15} aria-hidden="true" className="text-ink/50" />
        </button>

        <button
          type="button"
          aria-expanded={menuOpen}
          aria-controls="app-mobile-menu"
          aria-label={menuOpen ? 'Close menu' : 'Open menu'}
          onClick={toggleMenu}
          className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-ink/15 text-ink outline-offset-2 transition-colors hover:bg-ink/5 focus-visible:outline-2 focus-visible:outline-forest md:hidden"
        >
          {menuOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>
    </div>
  )
}

export default DashboardTopBar
