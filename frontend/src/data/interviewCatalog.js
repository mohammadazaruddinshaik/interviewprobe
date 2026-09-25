import { BookIcon, CodeIcon, CoffeeIcon, LayoutIcon, ServerIcon, SparkIcon, TargetIcon } from '../components/ui/icons.jsx'

// Ids match the backend's Role / InterviewTopic / Difficulty enums
// (backend/app/domain/enums.py) so this catalog can be swapped for a
// live API response without changing any component below it.

export const ROLES = [
  {
    id: 'AI_ENGINEER',
    label: 'AI Engineer',
    description: 'LLMs, RAG, embeddings, AI systems',
    icon: SparkIcon,
    topics: [
      { id: 'LLM_FUNDAMENTALS', label: 'LLM Fundamentals' },
      { id: 'RAG', label: 'RAG' },
      { id: 'EMBEDDINGS_VECTOR_DB', label: 'Embeddings / Vector DB' },
      { id: 'AI_AGENTS', label: 'AI Agents' },
      { id: 'LLM_EVALUATION', label: 'LLM Evaluation' },
      { id: 'AI_SYSTEM_DESIGN', label: 'AI System Design' },
    ],
  },
  {
    id: 'FRONTEND_DEVELOPER',
    label: 'Frontend Developer',
    description: 'JavaScript, React, CSS, web performance',
    icon: CodeIcon,
    topics: [
      { id: 'JAVASCRIPT', label: 'JavaScript' },
      { id: 'REACT', label: 'React' },
      { id: 'CSS', label: 'CSS' },
      { id: 'WEB_PERFORMANCE', label: 'Web Performance' },
      { id: 'BROWSER_FUNDAMENTALS', label: 'Browser Fundamentals' },
    ],
  },
  {
    id: 'BACKEND_DEVELOPER',
    label: 'Backend Developer',
    description: 'APIs, databases, scalability, system design',
    icon: ServerIcon,
    topics: [
      { id: 'BACKEND_RUNTIME', label: 'Backend Runtime' },
      { id: 'REST_APIS', label: 'REST APIs' },
      { id: 'DATABASES', label: 'Databases' },
      { id: 'CACHING', label: 'Caching' },
      { id: 'SYSTEM_DESIGN', label: 'System Design' },
    ],
  },
  {
    id: 'JAVA_DEVELOPER',
    label: 'Java Developer',
    description: 'Core Java, OOP, concurrency, Spring',
    icon: CoffeeIcon,
    topics: [
      { id: 'CORE_JAVA', label: 'Core Java' },
      { id: 'OOP', label: 'Object-Oriented Programming' },
      { id: 'COLLECTIONS', label: 'Collections' },
      { id: 'CONCURRENCY', label: 'Concurrency' },
      { id: 'JVM', label: 'JVM' },
      { id: 'SPRING', label: 'Spring' },
    ],
  },
  {
    id: 'SDE',
    label: 'Software Development Engineer',
    description: 'DSA, backend systems, and practical engineering',
    icon: TargetIcon,
    topics: [
      { id: 'DATA_STRUCTURES_ALGORITHMS', label: 'Data Structures & Algorithms' },
      { id: 'BACKEND_RUNTIME', label: 'Backend Runtime' },
      { id: 'REST_APIS', label: 'REST APIs' },
      { id: 'DATABASES', label: 'Databases' },
      { id: 'SYSTEM_DESIGN', label: 'System Design' },
    ],
  },
  {
    id: 'SDE_INTERN',
    label: 'SDE Intern',
    description: 'Programming fundamentals, DSA, and OOP basics',
    icon: BookIcon,
    topics: [
      { id: 'DATA_STRUCTURES_ALGORITHMS', label: 'Data Structures & Algorithms' },
      { id: 'OOP', label: 'Object-Oriented Programming' },
      { id: 'REST_APIS', label: 'REST APIs' },
    ],
  },
  {
    id: 'FULL_STACK_DEVELOPER',
    label: 'Full Stack Developer',
    description: 'Frontend, backend, APIs, and databases end to end',
    icon: LayoutIcon,
    topics: [
      { id: 'JAVASCRIPT', label: 'JavaScript' },
      { id: 'REACT', label: 'React' },
      { id: 'BACKEND_RUNTIME', label: 'Backend Runtime' },
      { id: 'REST_APIS', label: 'REST APIs' },
      { id: 'DATABASES', label: 'Databases' },
    ],
  },
]

export const DIFFICULTIES = [
  { id: 'EASY', label: 'Easy' },
  { id: 'MEDIUM', label: 'Medium' },
  { id: 'HARD', label: 'Hard' },
]

export const MIN_TOPICS = 1
export const MAX_TOPICS = 6
export const MIN_QUESTIONS = 3
export const MAX_QUESTIONS = 10
export const DEFAULT_QUESTION_COUNT = 6

// The candidate now only chooses a role — the Technical Round decides
// difficulty, topic breadth, and pacing itself (LangGraph adapts question
// difficulty/direction turn by turn regardless of this starting point).
// `POST /interviews` still requires `difficulty`/`topics`/`question_limit`
// (see backend/app/schemas/interview.py's CreateInterviewRequest — none of
// them have a server-side default), so the frontend derives them from the
// same catalog data above rather than asking the candidate: every topic in
// the role's own catalog entry (the full breadth `validate_role_topics`
// already allows for that role) at a fixed baseline difficulty and length.
export const DEFAULT_DIFFICULTY = 'MEDIUM'

export function getDefaultTopicsForRole(role) {
  return role.topics.map((topic) => topic.id).slice(0, MAX_TOPICS)
}

// Display-label lookups by raw backend enum value, for pages (like the
// interview workspace) that only receive the enum id from the API and
// need the same human-readable labels used during setup.
export const ROLE_LABELS = Object.fromEntries(ROLES.map((role) => [role.id, role.label]))
export const DIFFICULTY_LABELS = Object.fromEntries(
  DIFFICULTIES.map((difficulty) => [difficulty.id, difficulty.label]),
)
export const TOPIC_LABELS = Object.fromEntries(
  ROLES.flatMap((role) => role.topics).map((topic) => [topic.id, topic.label]),
)
