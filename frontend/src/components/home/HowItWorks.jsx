const STEPS = [
  {
    number: '01',
    title: 'Choose your interview',
    description: 'Select your role, difficulty and topics.',
  },
  {
    number: '02',
    title: 'Think. Explain. Respond.',
    description: 'Answer realistic technical questions that adapt to your responses.',
  },
  {
    number: '03',
    title: 'Learn from your performance.',
    description: 'Get scores, strengths, weaknesses, and evidence from your answers.',
  },
]

function HowItWorks() {
  return (
    <section id="how-it-works" className="border-t border-line/70 bg-cream-soft/40">
      <div className="mx-auto max-w-7xl px-6 py-24">
        <h2 className="max-w-xl text-4xl font-semibold leading-tight tracking-tight text-ink sm:text-5xl">
          Practice the way
          <br />
          real interviews happen.
        </h2>

        <div className="mt-16 grid grid-cols-1 gap-12 md:grid-cols-3 md:gap-10">
          {STEPS.map((step) => (
            <div key={step.number} className="border-t border-line pt-8">
              <span className="block text-6xl font-semibold leading-none text-accent/25 sm:text-7xl">
                {step.number}
              </span>
              <h3 className="mt-5 text-xl font-semibold text-ink">{step.title}</h3>
              <p className="mt-2 leading-relaxed text-muted">{step.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

export default HowItWorks
