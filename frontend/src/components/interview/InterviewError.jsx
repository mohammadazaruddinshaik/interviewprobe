import Button from '../ui/Button.jsx'

function InterviewError({ message, onRetry, children }) {
  return (
    <div className="mx-auto max-w-md px-6 pt-24 text-center sm:px-8">
      <p role="alert" aria-live="assertive" className="text-base text-ink">
        {message}
      </p>
      {onRetry && (
        <Button onClick={onRetry} variant="secondary" className="mt-6">
          Try again
        </Button>
      )}
      {children}
    </div>
  )
}

export default InterviewError
