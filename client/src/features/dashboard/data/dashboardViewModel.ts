import type { AuthUser } from '@/lib/auth'

// Display-ready shapes consumed by the presentational dashboard components. They are produced by
// lib/dashboardMapper.ts from the real API response; nothing here is static content.

/** The one thing the dashboard asks the candidate to do next. */
export interface PrimaryView {
  kind: 'continue' | 'start-created' | 'new'
  heading: string
  /** The role of the existing interview; null when there is none. */
  role: string | null
  /** Plain factual status ("In progress", "Not started") or an invitation line when there is no interview. */
  note: string
  cta: string
  ctaHref: string
}

export interface SummaryItem {
  label: string
  value: string
  /** Secondary line, only when the backend has something real to say. */
  context: string | null
}

export interface RecentInterviewView {
  id: string
  role: string
  /** "Completed 12 minutes ago" / "Completed Sep 28, 2026". */
  completed: string
  /** "2.5 / 10", or null when the interview has no evaluation. */
  score: string | null
  href: string
}

export interface StreakDayView {
  /** "Mon". */
  label: string
  /** Full text for assistive technology, e.g. "Monday: interview completed". */
  title: string
  active: boolean
  today: boolean
}

export interface StreakView {
  days: number
  /** "3 days" or "No active streak". */
  title: string
  week: StreakDayView[]
}

export interface DashboardView {
  greeting: string
  user: AuthUser | null
  primary: PrimaryView
  /** Empty when nothing has been completed yet: no zeros are shown as if they were results. */
  summary: SummaryItem[]
  streak: StreakView
  recentInterviews: RecentInterviewView[]
}
