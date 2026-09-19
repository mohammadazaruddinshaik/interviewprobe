import Button from '../ui/Button.jsx'

function FinalCTA() {
  return (
    <section className="px-6 py-20">
      <div className="relative mx-auto max-w-5xl overflow-hidden rounded-3xl bg-ink px-8 py-16 text-center sm:px-16">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-accent/20 blur-3xl"
        />
        <h2 className="relative text-3xl font-semibold tracking-tight text-cream sm:text-4xl">
          Ready to practice?
        </h2>
        <p className="relative mx-auto mt-4 max-w-md text-cream/70">
          Build confidence by doing the interview before the interview.
        </p>
        <div className="relative mt-9">
          <Button to="/interview/new" variant="inverse" withArrow>
            Start an interview
          </Button>
        </div>
      </div>
    </section>
  )
}

export default FinalCTA
