import { apiRequest } from '@/lib/api'

// Typed mirror of GET /api/v1/dashboard (the `data` payload). Enum-like values
// stay plain strings; mapping to display labels happens in ../lib.

export interface DashboardStats {
  completed_interviews: number
  average_score: number | null
  completed_this_month: number
  average_score_change: number | null
  topics_practiced: number
}

export interface DashboardNextInterview {
  id: string
  role: string
  /** Planner-owned: null while the interview is CREATED. */
  difficulty: string | null
  question_limit: number | null
  status: string
}

export interface DashboardRecentInterview {
  id: string
  role: string
  difficulty: string
  status: string
  topics: string[]
  overall_score: number | null
  completed_at: string | null
  created_at: string
}

export interface DashboardActivityDay {
  date: string
  active: boolean
}

export interface DashboardStreak {
  days: number
  activity: DashboardActivityDay[]
}

/** The `data` payload of the dashboard response (apiRequest already unwraps the `{ data }` envelope). */
export interface DashboardApiResponse {
  stats: DashboardStats
  next_interview: DashboardNextInterview | null
  recent_interviews: DashboardRecentInterview[]
  streak: DashboardStreak
}

export function fetchDashboard(): Promise<DashboardApiResponse> {
  return apiRequest<DashboardApiResponse>('/dashboard')
}
