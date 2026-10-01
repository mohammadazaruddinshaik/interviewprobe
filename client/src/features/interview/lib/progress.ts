const TYPE_LABELS: Record<string, string> = {
  INITIAL: 'Opening question',
  FOLLOW_UP: 'Follow-up',
  CLARIFICATION: 'Clarification',
  DEEP_DIVE: 'Deep dive',
  CHALLENGE: 'Challenge',
  TOPIC_TRANSITION: 'Topic transition',
}

export const questionTypeLabel = (type: string) =>
  TYPE_LABELS[type] ?? type.charAt(0) + type.slice(1).toLowerCase().replace(/_/g, ' ')
