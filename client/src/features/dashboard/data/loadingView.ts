import { STATIC_INTRO, STATIC_PROMPT } from '../content/staticContent'
import type { DashboardView } from './dashboardViewModel'

// Representative (never shown) content used only to size skeleton placeholders.
export const LOADING_VIEW: DashboardView = {
  greeting: { greeting: 'Good morning, Firstname.', prompt: STATIC_PROMPT, intro: STATIC_INTRO },
  userName: 'Account',
  nextInterview: {
    label: 'YOUR NEXT INTERVIEW',
    role: 'AI Engineer',
    subtitle: 'Medium difficulty',
    chips: ['8 questions', 'In progress', 'Adaptive', 'AI Interviewer'],
    cta: 'Start Interview',
    ctaHref: '#start-interview',
  },
  stats: [
    { value: '00', label: 'Interviews completed', context: '+0 this month' },
    { value: '00%', label: 'Average performance', context: '+00% vs last month' },
    { value: '00', label: 'Topics practiced', context: null },
  ],
  recentInterviews: [1, 2, 3].map((n) => ({
    id: `loading-${n}`,
    role: 'Backend Engineer',
    focus: 'System Design, APIs, Databases',
    difficulty: 'Medium',
    href: '#',
    score: '00%',
    date: '2 hours ago',
  })),
  streak: {
    days: 0,
    title: '00 days',
    message: 'Keep your streak going!',
    week: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((label) => ({ label, state: 'upcoming' as const })),
  },
  practicedTopics: { count: 0, summary: '00 topics practiced across your interviews.', recentTopics: [] },
}
