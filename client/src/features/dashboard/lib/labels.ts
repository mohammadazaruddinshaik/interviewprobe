// Display labels for backend enum values (backend/app/domain/enums.py).
// Unknown values fall back to a readable title-cased form rather than crashing.

const TOPIC_LABELS: Record<string, string> = {
  LLM_FUNDAMENTALS: 'LLM Fundamentals',
  RAG: 'RAG',
  EMBEDDINGS_VECTOR_DB: 'Embeddings & Vector DBs',
  AI_AGENTS: 'AI Agents',
  LLM_EVALUATION: 'LLM Evaluation',
  AI_SYSTEM_DESIGN: 'AI System Design',
  JAVASCRIPT: 'JavaScript',
  REACT: 'React',
  CSS: 'CSS',
  WEB_PERFORMANCE: 'Web Performance',
  BROWSER_FUNDAMENTALS: 'Browser Fundamentals',
  BACKEND_RUNTIME: 'Backend Runtime',
  REST_APIS: 'REST APIs',
  DATABASES: 'Databases',
  CACHING: 'Caching',
  SYSTEM_DESIGN: 'System Design',
  CORE_JAVA: 'Core Java',
  OOP: 'OOP',
  COLLECTIONS: 'Collections',
  CONCURRENCY: 'Concurrency',
  JVM: 'JVM',
  SPRING: 'Spring',
  DATA_STRUCTURES_ALGORITHMS: 'Data Structures & Algorithms',
}

const ROLE_LABELS: Record<string, string> = {
  AI_ENGINEER: 'AI Engineer',
  FRONTEND_DEVELOPER: 'Frontend Developer',
  BACKEND_DEVELOPER: 'Backend Developer',
  JAVA_DEVELOPER: 'Java Developer',
  SDE: 'SDE',
  SDE_INTERN: 'SDE Intern',
  FULL_STACK_DEVELOPER: 'Full Stack Developer',
}

const DIFFICULTY_LABELS: Record<string, string> = {
  EASY: 'Easy',
  MEDIUM: 'Medium',
  HARD: 'Hard',
}

function titleCase(value: string): string {
  return value
    .toLowerCase()
    .split('_')
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

const labelFrom = (table: Record<string, string>) => (value: string) => table[value] ?? titleCase(value)

export const topicLabel = labelFrom(TOPIC_LABELS)
export const roleLabel = labelFrom(ROLE_LABELS)
export const difficultyLabel = labelFrom(DIFFICULTY_LABELS)

export function interviewStatusLabel(status: string): string {
  if (status === 'IN_PROGRESS') return 'In progress'
  if (status === 'CREATED') return 'Not started'
  return titleCase(status)
}
