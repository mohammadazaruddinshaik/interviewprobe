const VALUE_POINTS = [
  {
    number: '01',
    title: 'Adaptive Questions',
    text: 'Questions change based on how you answer.',
  },
  {
    number: '02',
    title: 'Role-Aware Practice',
    text: 'Prepare against the competencies your target role actually requires.',
  },
  {
    number: '03',
    title: 'Actionable Feedback',
    text: 'Understand what was strong, what was weak, and what to improve next.',
  },
]

function FeaturesSection() {
  return (
    <section id="features" aria-labelledby="features-heading" className="px-4 pb-[88px] pt-[88px] md:pt-[104px]">
      <div className="mx-auto grid max-w-[1054px] gap-14 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] lg:items-center lg:gap-x-10">
        <div>
          <p className="flex items-center gap-2.5 text-[11px] font-semibold tracking-[0.18em] text-ink/60">
            <span aria-hidden="true" className="h-2 w-2 rounded-[2px] bg-yellow" />
            INTERVIEWS SHOULDN'T FEEL SCRIPTED.
          </p>

          <h2
            id="features-heading"
            className="mt-5 font-display text-[34px] font-extrabold leading-[1.08] tracking-[-0.02em] text-deep sm:text-[40px] lg:text-[46px]"
          >
            Stop Practicing
            <br />
            the Same Questions.
          </h2>

          <p className="mt-5 max-w-[470px] font-serif text-[17px] leading-[1.45] text-ink sm:text-lg">
            Most interview practice gives you a fixed list of questions. InterviewProbe adapts the
            conversation to your role, experience, answers, and areas that need deeper probing.
          </p>

          <ul className="mt-9 border-t border-ink/15">
            {VALUE_POINTS.map((point) => (
              <li key={point.number} className="flex gap-5 border-b border-ink/15 py-5">
                <span className="w-7 shrink-0 pt-0.5 font-display text-[13px] font-extrabold tracking-[0.04em] text-forest/60">
                  {point.number}
                </span>
                <div>
                  <h3 className="text-[15px] font-semibold text-deep">{point.title}</h3>
                  <p className="mt-1 text-[13.5px] leading-[1.5] text-ink/65">{point.text}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <div className="relative mx-auto aspect-[1075/885] w-full max-w-[640px] overflow-hidden [-webkit-mask-composite:source-in] [-webkit-mask-image:linear-gradient(to_right,transparent,#000_22px,#000_calc(100%-22px),transparent),linear-gradient(to_bottom,transparent,#000_22px,#000_calc(100%-22px),transparent)] [mask-composite:intersect] [mask-image:linear-gradient(to_right,transparent,#000_22px,#000_calc(100%-22px),transparent),linear-gradient(to_bottom,transparent,#000_22px,#000_calc(100%-22px),transparent)] lg:max-w-none">
          <img
            src="/assets/landing/adaptive-interview-flow.png"
            alt="An adaptive interview flow: a question, the candidate's answer, an AI probe that digs into the answer, and a deeper follow-up question."
            width={1586}
            height={992}
            loading="lazy"
            decoding="async"
            className="absolute -left-[26.5%] -top-[4.5%] h-auto w-[147.5%] max-w-none"
          />
        </div>
      </div>
    </section>
  )
}

export default FeaturesSection
