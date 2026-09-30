/** "8.1" — backend scores are 0-10 and are shown as X.X / 10 (never as a percentage). Zero is a real score. */
export const formatScore = (score: number) => score.toFixed(1)

/** Accessible text, e.g. "Reasoning, 7.8 out of 10". */
export const scoreLabel = (name: string, score: number) => `${name}, ${formatScore(score)} out of 10`

/** Bar fill for a 0-10 score, clamped. Visual only: the number is the source of truth. */
export const barWidth = (score: number) => `${Math.min(100, Math.max(0, score * 10))}%`
