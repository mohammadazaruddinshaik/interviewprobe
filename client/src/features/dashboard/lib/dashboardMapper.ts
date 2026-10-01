import type { AuthUser } from '@/lib/auth'
import type { DashboardApiResponse } from '../api/dashboardApi'
import type { DashboardView, PrimaryView, RecentInterviewView, StreakView, SummaryItem } from '../data/dashboardViewModel'
import { roleLabel } from './labels'
import { formatRelativeTime } from './relativeTime'

const NEW_INTERVIEW_HREF = '/app/interviews/new'

// Scores are 0-10 and shown exactly as on the result page: "X.X / 10".
const formatScore = (score: number) => `${score.toFixed(1)} / 10`

function greetingFor(user: AuthUser | null, now: Date) {
  const hour = now.getHours()
  const period = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening'
  const firstName = user?.name.trim().split(/\s+/)[0]
  return firstName ? `${period}, ${firstName}.` : `${period}.`
}

/**
 * Only the role and the lifecycle status of the existing interview are used. Difficulty, question limit and planned
 * topics are planner internals and are deliberately never read here.
 */
function mapPrimary(next: DashboardApiResponse['next_interview']): PrimaryView {
  if (!next) {
    return {
      kind: 'new',
      heading: 'Start an interview',
      role: null,
      note: 'Choose a role and let the interviewer adapt the conversation to you.',
      cta: 'Start Interview',
      ctaHref: NEW_INTERVIEW_HREF,
    }
  }
  // Both existing interviews are opened in the room, which resumes an in-progress one and offers to start a new one.
  const href = `/app/interviews/${encodeURIComponent(next.id)}`
  if (next.status === 'IN_PROGRESS') {
    return { kind: 'continue', heading: 'Continue your interview', role: roleLabel(next.role), note: 'In progress', cta: 'Continue Interview', ctaHref: href }
  }
  return { kind: 'start-created', heading: 'Your interview is ready', role: roleLabel(next.role), note: 'Not started', cta: 'Start Interview', ctaHref: href }
}

function mapSummary(stats: DashboardApiResponse['stats']): SummaryItem[] {
  if (stats.completed_interviews === 0) return []
  const items: SummaryItem[] = [
    { label: 'Interviews completed', value: String(stats.completed_interviews), context: null },
    { label: 'Average score', value: stats.average_score === null ? '—' : formatScore(stats.average_score), context: null },
    { label: 'Completed this month', value: String(stats.completed_this_month), context: null },
  ]
  const change = stats.average_score_change
  // Shown only when the backend computed a real comparison with last month.
  if (change !== null) {
    items.push({ label: 'Average score change', value: `${change >= 0 ? '+' : '−'}${Math.abs(Math.round(change * 100))}%`, context: 'vs last month' })
  }
  return items
}

const WEEKDAY = new Intl.DateTimeFormat('en-US', { weekday: 'short', timeZone: 'UTC' })
const WEEKDAY_LONG = new Intl.DateTimeFormat('en-US', { weekday: 'long', timeZone: 'UTC' })

/** The backend's last seven UTC days, oldest first, ending today. Nothing is added or inferred. */
function mapStreak(streak: DashboardApiResponse['streak']): StreakView {
  const last = streak.activity.length - 1
  return {
    days: streak.days,
    title: streak.days > 0 ? `${streak.days} ${streak.days === 1 ? 'day' : 'days'}` : 'No active streak',
    week: streak.activity.map((day, index) => {
      const date = new Date(`${day.date}T00:00:00Z`)
      return {
        label: WEEKDAY.format(date),
        title: `${WEEKDAY_LONG.format(date)}: ${day.active ? 'interview completed' : 'no interview completed'}`,
        active: day.active,
        today: index === last,
      }
    }),
  }
}

function mapRecent(items: DashboardApiResponse['recent_interviews'], now: number): RecentInterviewView[] {
  return items.map((item) => ({
    id: item.id,
    role: roleLabel(item.role),
    completed: `Completed ${formatRelativeTime(item.completed_at ?? item.created_at, now)}`,
    score: item.overall_score === null ? null : formatScore(item.overall_score),
    href: `/app/interviews/${encodeURIComponent(item.id)}/result`,
  }))
}

export function mapDashboard(api: DashboardApiResponse, user: AuthUser | null, now: Date = new Date()): DashboardView {
  return {
    greeting: greetingFor(user, now),
    user,
    primary: mapPrimary(api.next_interview),
    summary: mapSummary(api.stats),
    streak: mapStreak(api.streak),
    recentInterviews: mapRecent(api.recent_interviews, now.getTime()),
  }
}
