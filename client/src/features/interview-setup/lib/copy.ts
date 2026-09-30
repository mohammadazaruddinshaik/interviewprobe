// Presentation copy only (not backend claims). Unknown difficulty values fall back gracefully.
const DIFFICULTY_COPY: Record<string, { label: string; description: string }> = {
  EASY: { label: 'Easy', description: 'Core concepts' },
  MEDIUM: { label: 'Medium', description: 'Applied reasoning' },
  HARD: { label: 'Hard', description: 'Depth and trade-offs' },
}

export function difficultyCopy(value: string) {
  const known = DIFFICULTY_COPY[value]
  if (known) return known
  const label = value.charAt(0) + value.slice(1).toLowerCase()
  return { label, description: '' }
}

export const DEFAULT_DIFFICULTY = 'MEDIUM'
export const DEFAULT_QUESTION_LIMIT = 5
/** How many topics are preselected when a role is first shown or its topics must be reset. */
export const DEFAULT_TOPIC_COUNT = 3
