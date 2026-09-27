// A purely visual progress indicator — "AI Preparation" is not a real
// configuration step the candidate goes through; the backend prepares the
// interview automatically once "Start Interview" is pressed. This never
// becomes an interactive/clickable step and never exposes any setting.
// Deliberately compact: small numbered circles + a thin connector + a
// short label, not a large multi-line section.
const STEPS = [
  { number: 1, title: 'Role' },
  { number: 2, title: 'Prepare' },
  { number: 3, title: 'Start' },
]

function InterviewStepper({ activeStep = 1 }) {
  return (
    <ol className="flex items-center gap-1 sm:gap-2">
      {STEPS.map((step, index) => {
        const isActive = step.number === activeStep
        return (
          <li key={step.number} className="flex min-w-0 flex-1 items-center gap-1.5 sm:gap-2">
            <span
              className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-semibold sm:h-6 sm:w-6 sm:text-[11px] ${
                isActive ? 'bg-primary text-white' : 'bg-glass/80 text-muted'
              }`}
              aria-current={isActive ? 'step' : undefined}
            >
              {step.number}
            </span>
            <p className={`min-w-0 truncate text-xs font-medium ${isActive ? 'text-ink' : 'text-muted'}`}>
              {step.title}
            </p>
            {index < STEPS.length - 1 && (
              <span aria-hidden="true" className="hidden h-px min-w-2 flex-1 bg-line sm:block" />
            )}
          </li>
        )
      })}
    </ol>
  )
}

export default InterviewStepper
