import type { InterviewResult } from '../types/result'

export type ResultState =
  | { phase: 'loading' } // brief skeleton
  | { phase: 'evaluating' } // slow request or EVALUATION_BUSY retries: "we're preparing your evaluation"
  | { phase: 'ready'; result: InterviewResult }
  | { phase: 'notFound' | 'unauthenticated' }
  | { phase: 'notCompleted'; status: string | null } // status from GET /interviews/{id}; null if it couldn't be read
  | { phase: 'failed'; reason: 'evaluation' | 'load' }

export type ResultAction =
  | { type: 'RESET' }
  | { type: 'SLOW' }
  | { type: 'OUTCOME'; state: ResultState }

export function resultReducer(state: ResultState, action: ResultAction): ResultState {
  switch (action.type) {
    case 'RESET':
      return { phase: 'loading' }
    case 'SLOW':
      return state.phase === 'loading' ? { phase: 'evaluating' } : state
    case 'OUTCOME':
      return action.state
  }
}
