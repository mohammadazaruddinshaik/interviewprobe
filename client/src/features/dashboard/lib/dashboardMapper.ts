import type { AuthUser } from '@/lib/auth'
import type { DashboardApiResponse } from '../api/dashboardApi'
import { STATIC_INTERVIEW_CHIPS, STATIC_INTRO, STATIC_PROMPT } from '../content/staticContent'
import type {
  DashboardView,
  DayState,
  NextInterviewView,
  PracticedTopicsView,
  RecentInterviewView,
  StatView,
  StreakView,
} from '../data/dashboardViewModel'
import { difficultyLabel, interviewStatusLabel, roleLabel, topicLabel } from './labels'
import { formatRelativeTime } from './relativeTime'

const NEW_INTERVIEW_HREF = '/app/interviews/new'

/** Backend scores are 0-10; the UI shows percentages. */
const scoreToPercent = (score: number) => `${Math.round(score * 10)}%`

function greetingFor(user: AuthUser | null, now: Date) {
  const hour = now.getHours()
  const period = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening'
  const firstName = user?.name.trim().split(/\s+/)[0]
  return { greeting: firstName ? `${period}, ${firstName}.` : `${period}.`, prompt: STATIC_PROMPT, intro: STATIC_INTRO }
}

function mapNextInterview(next: DashboardApiResponse['next_interview']): NextInterviewView {
  if (!next) {
    return {
      label: 'YOUR NEXT INTERVIEW',
      role: 'Nothing queued',
      subtitle: 'Start a new interview tailored to your target role.',
      chips: STATIC_INTERVIEW_CHIPS,
      cta: 'Start an Interview',
      ctaHref: NEW_INTERVIEW_HREF,
    }
  }
  return {
    label: 'YOUR NEXT INTERVIEW',
    role: roleLabel(next.role),
    subtitle: `${difficultyLabel(next.difficulty)} difficulty`,
    chips: [`${next.question_limit} questions`, interviewStatusLabel(next.status), ...STATIC_INTERVIEW_CHIPS],
    cta: next.status === 'IN_PROGRESS' ? 'Continue Interview' : 'Start Interview',
    // Resume the existing interview instead of creating a second one.
    ctaHref: `/app/interviews/${next.id}`,
  }
}

function mapStats(stats: DashboardApiResponse['stats']): StatView[] {
  const change = stats.average_score_change
  const changeText =
    change === null ? null : `${change >= 0 ? '+' : '−'}${Math.abs(Math.round(change * 100))}% vs last month`
  return [
    {
      value: String(stats.completed_interviews),
      label: 'Interviews completed',
      context: stats.completed_this_month > 0 ? `+${stats.completed_this_month} this month` : 'None this month',
    },
    {
      value: stats.average_score === null ? '—' : scoreToPercent(stats.average_score),
      label: 'Average performance',
      context: changeText,
    },
    { value: String(stats.topics_practiced), label: 'Topics practiced', context: null },
  ]
}

function mapRecent(items: DashboardApiResponse['recent_interviews'], now: number): RecentInterviewView[] {
  return items.map((item) => ({
    id: item.id,
    role: roleLabel(item.role),
    focus: item.topics.length > 0 ? item.topics.map(topicLabel).join(', ') : '—',
    difficulty: difficultyLabel(item.difficulty),
    href: `/app/interviews/${item.id}/result`,
    score: item.overall_score === null ? null : scoreToPercent(item.overall_score),
    date: formatRelativeTime(item.completed_at ?? item.created_at, now),
  }))
}

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

/**
 * The backend's streak.activity is the last 7 UTC days ending "today" (UTC).
 * It is laid onto the existing Mon-Sun week that contains that UTC "today":
 * every day of that week is inside the 7-day window or still in the future.
 */
function mapStreak(streak: DashboardApiResponse['streak']): StreakView {
  const active = new Map(streak.activity.map((day) => [day.date, day.active]))
  const todayIso = streak.activity.at(-1)?.date
  const today = todayIso ? new Date(`${todayIso}T00:00:00Z`) : new Date()
  const mondayOffset = (today.getUTCDay() + 6) % 7 // getUTCDay: Sun=0 -> Monday-based index
  const week = WEEKDAYS.map((label, index) => {
    const date = new Date(today.getTime() + (index - mondayOffset) * 86_400_000).toISOString().slice(0, 10)
    const offset = index - mondayOffset
    let state: DayState
    if (offset > 0) state = 'upcoming'
    else if (active.get(date)) state = 'done'
    else state = offset === 0 ? 'today' : 'missed'
    return { label, state }
  })
  return {
    days: streak.days,
    title: `${streak.days} ${streak.days === 1 ? 'day' : 'days'}`,
    message: streak.days > 0 ? 'Keep your streak going!' : 'Complete an interview to start your streak.',
    week,
  }
}

function mapPracticedTopics(
  stats: DashboardApiResponse['stats'],
  recent: DashboardApiResponse['recent_interviews'],
): PracticedTopicsView {
  const recentTopics = [...new Set(recent.flatMap((item) => item.topics))].map(topicLabel)
  const n = stats.topics_practiced
  return {
    count: n,
    summary: n === 0 ? 'No topics practiced yet.' : `${n} ${n === 1 ? 'topic' : 'topics'} practiced across your interviews.`,
    recentTopics,
  }
}

export function mapDashboard(api: DashboardApiResponse, user: AuthUser | null, now: Date = new Date()): DashboardView {
  return {
    greeting: greetingFor(user, now),
    userName: user?.name ?? 'Account',
    nextInterview: mapNextInterview(api.next_interview),
    stats: mapStats(api.stats),
    recentInterviews: mapRecent(api.recent_interviews, now.getTime()),
    streak: mapStreak(api.streak),
    practicedTopics: mapPracticedTopics(api.stats, api.recent_interviews),
  }
}
