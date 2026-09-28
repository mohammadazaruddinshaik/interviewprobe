import InterviewProbeLoader from '../ui/InterviewProbeLoader.jsx'

function InterviewLoading() {
  return (
    <div className="mx-auto flex max-w-md flex-1 flex-col items-center justify-center px-6 py-20 text-center sm:px-8" aria-busy="true">
      <p className="sr-only" role="status">
        Loading your interview…
      </p>
      <InterviewProbeLoader label="Setting up your interview" />
    </div>
  )
}

export default InterviewLoading
