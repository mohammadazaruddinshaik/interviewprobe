function ScoreBar({ label, score }) {
  const percent = Math.max(0, Math.min(100, (score / 10) * 100))

  return (
    <div>
      <div className="flex items-baseline justify-between text-sm">
        <span className="font-medium text-ink">{label}</span>
        <span className="text-muted">{score.toFixed(1)} / 10</span>
      </div>
      <div
        role="progressbar"
        aria-valuenow={Number(score.toFixed(1))}
        aria-valuemin={0}
        aria-valuemax={10}
        aria-label={`${label}: ${score.toFixed(1)} out of 10`}
        className="mt-2 h-2 w-full overflow-hidden rounded-full bg-line"
      >
        <div
          className="h-full rounded-full bg-accent transition-[width] duration-700 ease-out motion-reduce:transition-none"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  )
}

export default ScoreBar
