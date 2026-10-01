import { FileText, LayoutGrid, Plus } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

export interface NavItem {
  label: string
  icon: LucideIcon
  href: string
}

/** The authenticated app's navigation. Every entry is a page that exists. */
export const APP_NAV: NavItem[] = [
  { label: 'Dashboard', icon: LayoutGrid, href: '/app' },
  { label: 'Results', icon: FileText, href: '/app/results' },
  { label: 'New interview', icon: Plus, href: '/app/interviews/new' },
]
