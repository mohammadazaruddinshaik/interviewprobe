import type { LearningItem } from '../data/dashboardViewModel'

// STATIC PRODUCT CONTENT — not fetched from the backend (no API exists for it yet).

/** Presentation-only labels describing how every InterviewProbe interview works. */
export const STATIC_INTERVIEW_CHIPS = ['Adaptive', 'AI Interviewer']

export const STATIC_PROMPT = 'Ready for your next interview?'
export const STATIC_INTRO = 'Pick up where you left off or start a new interview tailored to your target role.'

export const CONTINUE_LEARNING: LearningItem[] = [
  { title: 'System Design Fundamentals', detail: '8 lessons · 1 hour' },
  { title: 'Database Indexing', detail: '6 lessons · 45 min' },
  { title: 'OS Concepts for Interviews', detail: '5 lessons · 40 min' },
]
