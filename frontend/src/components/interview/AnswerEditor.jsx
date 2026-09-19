import Button from '../ui/Button.jsx'

const MAX_ANSWER_LENGTH = 10_000

function AnswerEditor({ value, onChange, onSubmit, submitting }) {
  const canSubmit = value.trim().length > 0 && !submitting

  function handleKeyDown(event) {
    if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
      event.preventDefault()
      if (canSubmit) onSubmit()
    }
  }

  return (
    <section className="mx-auto max-w-3xl px-6 pb-20 pt-6 sm:px-8">
      <label htmlFor="interview-answer" className="text-sm font-medium text-ink">
        Your answer
      </label>
      <textarea
        id="interview-answer"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={handleKeyDown}
        disabled={submitting}
        placeholder="Explain your approach, reasoning, and trade-offs..."
        rows={10}
        maxLength={MAX_ANSWER_LENGTH}
        className="mt-3 w-full resize-y rounded-2xl border border-line bg-white/70 p-5 text-base leading-relaxed text-ink placeholder:text-ink/35 transition-colors duration-200 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20 disabled:cursor-not-allowed disabled:opacity-60"
      />

      <div className="mt-2 flex items-center justify-between text-xs text-muted">
        <span>⌘/Ctrl + Enter to submit</span>
        <span>
          {value.length.toLocaleString()} / {MAX_ANSWER_LENGTH.toLocaleString()}
        </span>
      </div>

      <div className="mt-5">
        <Button
          onClick={onSubmit}
          disabled={!canSubmit}
          aria-busy={submitting}
          variant="primary"
          withArrow={!submitting}
        >
          {submitting ? 'Evaluating your answer…' : 'Submit answer'}
        </Button>
      </div>
    </section>
  )
}

export default AnswerEditor
