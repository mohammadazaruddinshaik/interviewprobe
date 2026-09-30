import { apiRequest } from '@/lib/api'

// Catalog: GET /interviews/catalog (public; the backend is the source of truth for roles/topics/limits).

export interface CatalogTopic {
  value: string
  label: string
  description: string
}

export interface CatalogRole {
  value: string
  label: string
  description: string
  /** Only the topics valid for this role. */
  topics: CatalogTopic[]
}

export interface CatalogRange {
  min: number
  max: number
}

export interface InterviewCatalog {
  roles: CatalogRole[]
  difficulties: { value: string }[]
  question_limit: CatalogRange
  topic_limit: CatalogRange
}

export const fetchInterviewCatalog = () => apiRequest<InterviewCatalog>('/interviews/catalog')

// Creation + start (authenticated via the session cookie; no user id or token is ever sent).

export interface CreateInterviewPayload {
  role: string
  difficulty: string
  topics: string[]
  question_limit: number
}

export const createInterview = (payload: CreateInterviewPayload) =>
  apiRequest<{ id: string }>('/interviews', { method: 'POST', body: JSON.stringify(payload) })

export const startInterview = (id: string) =>
  apiRequest<{ session_id: string }>(`/interviews/${encodeURIComponent(id)}/start`, { method: 'POST' })
