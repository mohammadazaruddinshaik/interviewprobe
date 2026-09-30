// Display-ready shapes consumed by the presentational dashboard components.
// They are produced by lib/dashboardMapper.ts (from the API) — components never
// see raw API values or do conversions themselves.

export interface NextInterviewView {
  label: string
  /** Null when there is no real next interview (empty state). */
  role: string
  subtitle: string
  chips: string[]
  cta: string
  ctaHref: string
}

export interface StatView {
  value: string
  label: string
  /** Null when the backend has nothing truthful to say (no fabricated deltas). */
  context: string | null
}

export interface RecentInterviewView {
  id: string
  role: string
  focus: string
  difficulty: string
  /** Where the row leads: the completed interview's result page. */
  href: string
  /** Display score ("82%") or null when the interview has no evaluation. */
  score: string | null
  date: string
}

export type DayState = 'done' | 'today' | 'missed' | 'upcoming'

export interface StreakView {
  days: number
  title: string
  message: string
  week: { label: string; state: DayState }[]
}

export interface PracticedTopicsView {
  count: number
  summary: string
  /** Topics seen in the recent interviews shown above — no per-topic progress is claimed. */
  recentTopics: string[]
}

export interface LearningItem {
  title: string
  detail: string
}

export interface GreetingView {
  greeting: string
  prompt: string
  intro: string
}

export interface DashboardView {
  greeting: GreetingView
  userName: string
  nextInterview: NextInterviewView
  stats: StatView[]
  recentInterviews: RecentInterviewView[]
  streak: StreakView
  practicedTopics: PracticedTopicsView
}
