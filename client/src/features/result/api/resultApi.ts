import { apiRequest } from '@/lib/api'
import type { InterviewResult } from '../types/result'

/** The Result page is the only caller. The first request may generate the evaluation (a blocking LLM call). */
export const fetchInterviewResult = (id: string) =>
  apiRequest<InterviewResult>(`/interviews/${encodeURIComponent(id)}/result`)
