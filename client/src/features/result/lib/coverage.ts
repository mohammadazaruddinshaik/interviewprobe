import type { ResultTopic } from '../types/result'

/** PENDING = not reached; IN_PROGRESS and COMPLETED both mean covered (the final topic keeps IN_PROGRESS). */
export const isCovered = (topic: ResultTopic) => topic.status === 'IN_PROGRESS' || topic.status === 'COMPLETED'
