import Button from '../ui/Button.jsx'
import { CheckIcon } from '../ui/icons.jsx'

function InterviewComplete({ sessionId }) {
  return (
    <div className="mx-auto max-w-md px-6 pt-24 text-center sm:px-8">
      <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-accent-soft text-accent">
        <CheckIcon className="h-6 w-6" />
      </span>
      <h1 className="mt-5 text-2xl font-semibold text-ink">Interview complete.</h1>
      <p className="mt-2 text-muted">Your answers have been recorded.</p>
      <Button to={`/interview/${sessionId}/result`} variant="primary" withArrow className="mt-6">
        View results
      </Button>
    </div>
  )
}

export default InterviewComplete
