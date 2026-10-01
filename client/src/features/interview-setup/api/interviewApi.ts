import { apiRequest } from '@/lib/api'

// Catalog: GET /interviews/catalog (public; the backend is the source of truth for roles; topics, difficulty and length are planner decisions).

export interface CatalogRole {
  value: string
  label: string
  description: string
}

export interface InterviewCatalog {
  roles: CatalogRole[]
}

export const fetchInterviewCatalog = () => apiRequest<InterviewCatalog>('/interviews/catalog')

// Creation + start (authenticated via the session cookie; no user id or token is ever sent).

export interface CreateInterviewPayload {
  role: string
}

export const createInterview = (payload: CreateInterviewPayload) =>
  apiRequest<{ id: string }>('/interviews', { method: 'POST', body: JSON.stringify(payload) })

export interface ResumeUploadResult {
  session_id: string
  /** READY when the resume was read; FAILED when it couldn't be (the upload itself still returns 200). */
  status: 'READY' | 'FAILED' | string
}

/** Must happen after creation and BEFORE /start: the planner reads the resume once, at start. */
export function uploadResume(id: string, file: File) {
  const form = new FormData()
  form.append('resume', file)
  return apiRequest<ResumeUploadResult>(`/interviews/${encodeURIComponent(id)}/resume`, { method: 'POST', body: form })
}

export const startInterview = (id: string) =>
  apiRequest<{ session_id: string }>(`/interviews/${encodeURIComponent(id)}/start`, { method: 'POST' })
