import { BrandMark, CheckIcon } from '../ui/icons.jsx'

function ResultHeader({ roleLabel, difficultyLabel }) {
  return (
    <header className="border-b border-line/70">
      <div className="mx-auto flex max-w-3xl items-start justify-between gap-6 px-6 py-5 sm:px-8">
        <div>
          <div className="flex items-center gap-1.5 text-ink">
            <BrandMark className="h-4 w-4 text-accent" />
            <span className="text-sm font-semibold tracking-tight">InterviewProbe</span>
          </div>
          {roleLabel && <p className="mt-2.5 text-sm font-medium text-ink">{roleLabel}</p>}
          {difficultyLabel && <p className="text-xs text-muted">{difficultyLabel}</p>}
        </div>

        <div className="flex items-center gap-1.5 rounded-full bg-accent-soft px-3 py-1.5 text-xs font-semibold text-accent">
          <CheckIcon className="h-3.5 w-3.5" />
          Interview complete
        </div>
      </div>
    </header>
  )
}

export default ResultHeader
