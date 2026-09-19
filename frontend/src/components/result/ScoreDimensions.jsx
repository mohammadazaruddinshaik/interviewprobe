import ScoreBar from './ScoreBar.jsx'

function ScoreDimensions({ evaluation }) {
  const dimensions = [
    { label: 'Technical Knowledge', score: evaluation.technical_knowledge_score },
    { label: 'Reasoning', score: evaluation.reasoning_score },
    { label: 'Depth', score: evaluation.depth_score },
    { label: 'Communication', score: evaluation.communication_score },
  ]

  return (
    <section className="border-t border-line/70">
      <div className="mx-auto max-w-3xl px-6 py-10 sm:px-8">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">Performance dimensions</h2>
        <div className="mt-6 flex flex-col gap-6">
          {dimensions.map((dimension) => (
            <ScoreBar key={dimension.label} label={dimension.label} score={dimension.score} />
          ))}
        </div>
      </div>
    </section>
  )
}

export default ScoreDimensions
