const A = "/assets/interviewprobe-landing";

const stages = [
  {
    num: "01",
    icon: `${A}/icons/conversation.svg`,
    title: "Converse",
    desc: "Have a real technical conversation with an interviewer.",
  },
  {
    num: "02",
    icon: `${A}/icons/probe.svg`,
    titleParts: [
      { text: "Get ", highlight: false },
      { text: "Probed", highlight: true },
    ],
    desc: "Go beyond surface-level answers with adaptive follow-ups.",
  },
  {
    num: "03",
    icon: `${A}/icons/feedback.svg`,
    titleParts: [
      { text: "Receive ", highlight: false },
      { text: "Feedback", highlight: true },
    ],
    desc: "Get detailed analysis on your strengths, gaps, and reasoning.",
  },
  {
    num: "04",
    icon: `${A}/icons/improve.svg`,
    title: "Improve",
    desc: "Practice, track progress, and get ready for real opportunities.",
  },
] as const;

export function ExperienceStrip() {
  return (
    <section
      className="relative border-t border-line"
      data-anim="strip"
    >
      <div className="relative mx-auto max-w-[1800px] px-[5vw] py-11 lg:py-14">
        {/* Probe line decoration */}
        <svg
          className="pointer-events-none absolute left-[3%] right-[3%] top-[-6px] hidden h-[90px] w-[94%] lg:block"
          viewBox="0 0 1400 80"
          fill="none"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <path
            d="M20 65 C200 8, 500 8, 700 40 C900 72, 1100 12, 1380 35"
            stroke="var(--color-ink)"
            strokeWidth="1.5"
            opacity="0.18"
          />
        </svg>

        {/* Green dot — left side */}
        <img
          src={`${A}/decorations/green-dot.svg`}
          alt=""
          className="absolute left-[3%] top-1/2 hidden h-4 w-4 -translate-y-1/2 lg:block"
          aria-hidden="true"
        />

        {/* Curve loop decoration */}
        <img
          src={`${A}/decorations/curve-loop.svg`}
          alt=""
          className="pointer-events-none absolute -top-4 right-[10%] hidden w-[240px] opacity-[0.18] lg:block"
          aria-hidden="true"
        />

        {/* Four columns */}
        <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-4 lg:gap-0">
          {stages.map((stage, i) => (
            <div
              key={stage.num}
              className={`relative lg:px-8 first:lg:pl-0 last:lg:pr-0 ${
                i < 3 ? "lg:border-r lg:border-line" : ""
              }`}
              data-anim="strip-col"
            >
              <span className="mb-4 block font-display text-[28px] font-bold text-ink">
                {stage.num}
              </span>
              <img
                src={stage.icon}
                alt=""
                className="mb-4 h-9 w-9"
                aria-hidden="true"
              />
              <h3 className="mb-2 font-display text-lg font-bold text-ink">
                {"title" in stage ? (
                  stage.title
                ) : (
                  <>
                    {stage.titleParts.map((p) =>
                      p.highlight ? (
                        <span key={p.text} className="text-green">
                          {p.text}
                        </span>
                      ) : (
                        <span key={p.text}>{p.text}</span>
                      ),
                    )}
                  </>
                )}
              </h3>
              <p className="text-[15px] leading-relaxed text-muted">
                {stage.desc}
              </p>
            </div>
          ))}
        </div>

        {/* Dotted connector between columns */}
        <svg
          className="pointer-events-none absolute left-[52%] top-[42%] hidden h-2 w-[18%] lg:block"
          viewBox="0 0 200 8"
          aria-hidden="true"
        >
          <line
            x1="0"
            y1="4"
            x2="200"
            y2="4"
            stroke="var(--color-forest)"
            strokeWidth="2.5"
            strokeDasharray="3 8"
            strokeLinecap="round"
            opacity="0.45"
          />
        </svg>

        {/* Green dot — right side */}
        <img
          src={`${A}/decorations/green-dot.svg`}
          alt=""
          className="absolute right-[4%] top-[30%] hidden h-4 w-4 lg:block"
          aria-hidden="true"
        />
      </div>

      {/* "From practice to progress." annotation */}
      <img
        src={`${A}/annotations/note-progress.svg`}
        alt=""
        className="pointer-events-none absolute bottom-4 right-[2%] hidden w-[130px] rotate-[3deg] lg:block xl:w-[150px]"
        data-anim="annotation"
        aria-hidden="true"
      />
    </section>
  );
}
