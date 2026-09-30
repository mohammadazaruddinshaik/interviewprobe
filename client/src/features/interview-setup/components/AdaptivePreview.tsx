// Decorative, compact question -> answer -> probe illustration (not the dashboard's AIInterviewerVisual).
const STEPS = [
  { key: 'q', label: 'INTERVIEWER', text: 'Walk me through how you’d approach this.', probe: false },
  { key: 'a', label: 'YOU', text: '…', probe: false },
  { key: 'p', label: 'AI PROBE', text: 'What would you change at ten times the scale?', probe: true },
]

function AdaptivePreview() {
  return (
    <div aria-hidden="true">
      <div className="relative mx-2 rounded-[14px] border border-forest/10 bg-forest/[0.04] p-3">
        <span className="absolute bottom-6 left-[19px] top-6 w-px bg-forest/15" />
        <div className="flex flex-col gap-2">
          {STEPS.map((step) => (
            <div key={step.key} className="relative pl-[22px]">
              <span
                className={`absolute left-px top-[11px] rounded-full border-[1.5px] ${
                  step.probe
                    ? 'left-0 h-[11px] w-[11px] border-yellow bg-forest ring-[3px] ring-yellow/35'
                    : 'h-[9px] w-[9px] border-forest/55 bg-cream'
                }`}
              />
              <div className={`rounded-[10px] border px-2.5 py-2 ${step.probe ? 'border-yellow bg-yellow/25' : 'border-ink/[0.08] bg-white/85'}`}>
                <p className="text-[9.5px] font-semibold tracking-[0.14em] text-ink/45">{step.label}</p>
                <p className="mt-0.5 font-serif text-[12.5px] leading-[1.3] text-deep">{step.text}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
      <p className="mt-2.5 text-center text-[12px] text-ink/60">Your interviewer adapts as you answer.</p>
    </div>
  )
}

export default AdaptivePreview
