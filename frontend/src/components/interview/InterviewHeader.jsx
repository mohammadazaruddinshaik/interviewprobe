import { BrandMark } from '../ui/icons.jsx'
import InterviewProgress from './InterviewProgress.jsx'

function InterviewHeader({ roleLabel, difficultyLabel, topicLabel, questionNumber, questionLimit }) {
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

        {questionNumber != null && questionLimit != null && (
          <div className="text-right">
            <p className="text-sm font-medium text-ink">
              Question {questionNumber} of {questionLimit}
            </p>
            {topicLabel && (
              <p className="mt-2.5 text-xs font-semibold uppercase tracking-wide text-accent">
                {topicLabel}
              </p>
            )}
            <InterviewProgress current={questionNumber} total={questionLimit} className="mt-2.5 justify-end" />
          </div>
        )}
      </div>
    </header>
  )
}

export default InterviewHeader
