const A = "/assets/interviewprobe-landing";

export function Hero() {
  return (
    <section
      className="relative overflow-hidden lg:min-h-[760px]"
      data-anim="hero"
    >
      {/* ─── LAYER 2: Yellow painterly brush (behind everything) ─── */}
      <img
        src={`${A}/decorations/yellow-highlighter.svg`}
        alt=""
        className="pointer-events-none absolute z-[1] hidden lg:block"
        style={{ left: "38vw", top: "37%", width: "20vw", opacity: 0.6 }}
        aria-hidden="true"
        data-anim="card"
      />

      {/* ─── LAYER 3: Left content (headline / copy / CTA) ─── */}
      <div className="relative z-30 px-[5vw]">
        <div className="pb-8 lg:min-h-[760px] lg:pb-0">
          <div className="pt-6 sm:pt-8 lg:max-w-[46vw] lg:pt-[6vh]">
            <h1
              data-anim="headline"
              className="font-display font-extrabold leading-[0.90] tracking-[-0.04em]"
              style={{ fontSize: "clamp(3rem, 6.5vw, 7rem)" }}
            >
              <span className="block text-ink">Real</span>
              <span className="block text-ink">Interviews</span>
              <span className="block">
                <span className="text-forest">Real </span>
                <span className="relative isolate inline-block text-ink">
                  Growth.
                  <svg
                    className="pointer-events-none absolute -z-10 select-none"
                    viewBox="20 60 370 180"
                    preserveAspectRatio="none"
                    style={{
                      left: "-8%",
                      bottom: "-8%",
                      width: "120%",
                      height: "60%",
                    }}
                    data-anim="highlight"
                    aria-hidden="true"
                  >
                    <path
                      d="M28 155 C100 110 190 180 260 130 C310 96 350 130 382 110"
                      fill="none"
                      stroke="#F5D63D"
                      strokeWidth="58"
                      strokeLinecap="round"
                      opacity=".9"
                    />
                    <path
                      d="M30 168 C110 130 195 194 270 145 C315 116 350 145 380 125"
                      fill="none"
                      stroke="#FFE879"
                      strokeWidth="9"
                      strokeLinecap="round"
                      opacity=".55"
                    />
                  </svg>
                </span>
              </span>
            </h1>

            {/* Mobile portrait */}
            <div
              className="relative mx-auto my-8 w-[280px] sm:w-[320px] lg:hidden"
              data-anim="portrait"
            >
              <div className="rotate-[2deg] rounded-2xl bg-paper p-1.5 shadow-md">
                <img
                  src={`${A}/hero/interviewer-portrait.png`}
                  alt="Technical interviewer in a professional setting"
                  className="w-full rounded-xl"
                />
              </div>
            </div>

            {/* Copy */}
            <p
              className="mt-5 max-w-lg text-base leading-relaxed text-muted lg:mt-8 lg:text-[1.15rem] lg:leading-relaxed"
              data-anim="copy"
            >
              Practice realistic technical interviews.
              <br />
              Get detailed feedback and improve faster —
              <br />
              with questions that adapt to how you think.
            </p>

            {/* CTA */}
            <div
              className="mt-6 flex flex-wrap items-center gap-5 lg:mt-9"
              data-anim="cta"
            >
              <a
                href="/setup"
                className="inline-flex items-center gap-2.5 rounded-full bg-forest px-8 py-4 font-display text-[15px] font-semibold text-white transition-colors hover:bg-green"
              >
                Start Practicing Free
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 64 64"
                  fill="none"
                  aria-hidden="true"
                >
                  <path
                    d="M16 48 L48 16 M29 16 H48 V35"
                    stroke="currentColor"
                    strokeWidth="5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </a>

              <a
                href="#demo"
                className="group inline-flex items-center gap-3 text-ink transition-colors hover:text-forest"
              >
                <img
                  src={`${A}/icons/play.svg`}
                  alt=""
                  className="h-11 w-11"
                  aria-hidden="true"
                />
                <span className="text-left">
                  <span className="block font-display text-sm font-semibold">
                    Watch Demo
                  </span>
                  <span className="text-xs text-muted">2 min</span>
                </span>
              </a>
            </div>

            {/* Brand statement */}
            <p
              className="mt-8 text-sm text-muted lg:mt-12"
              data-anim="social"
            >
              Built for engineers who want more than surface-level practice.
            </p>
          </div>
        </div>
      </div>

      {/* ─── LAYER 4/5: Desktop composition (portrait + cards) ─── */}
      <div
        className="pointer-events-none absolute inset-0 hidden lg:block"
        aria-label="Editorial hero composition"
      >
        {/* Portrait — CENTER ZONE */}
        <div
          className="absolute z-[10]"
          style={{ left: "46vw", top: "11%", width: "31vw" }}
          data-anim="portrait"
        >
          {/* Dot field — upper left */}
          <svg
            className="absolute -left-6 -top-6 h-20 w-20 opacity-25"
            aria-hidden="true"
          >
            {Array.from({ length: 25 }).map((_, i) => (
              <rect
                key={i}
                x={(i % 5) * 14 + 2}
                y={Math.floor(i / 5) * 14 + 2}
                width="3"
                height="3"
                rx="0.5"
                fill="#11140F"
              />
            ))}
          </svg>

          <div
            className="relative rotate-[2deg] bg-paper p-2.5 shadow-[0_6px_32px_rgba(0,0,0,0.10)]"
            style={{
              borderRadius: "18px 20px 16px 22px",
              border: "1.5px solid rgba(17,20,15,0.08)",
            }}
          >
            <img
              src={`${A}/hero/interviewer-portrait.png`}
              alt="Technical interviewer in a professional setting"
              className="w-full"
              style={{ borderRadius: "14px 16px 12px 18px" }}
            />
            <img
              src={`${A}/decorations/diagonal-scribble.svg`}
              alt=""
              className="absolute -left-5 -top-5 w-16 -rotate-12 opacity-35"
              aria-hidden="true"
            />
            <img
              src={`${A}/decorations/diagonal-scribble.svg`}
              alt=""
              className="absolute -bottom-5 -right-5 w-16 rotate-[168deg] opacity-35"
              aria-hidden="true"
            />
          </div>

          {/* Arrow pointing to portrait */}
          <img
            src={`${A}/decorations/arrow-02.svg`}
            alt=""
            className="absolute -top-14 left-[50%] w-[70px]"
            aria-hidden="true"
          />
        </div>

        {/* Question card — upper-right edge of portrait */}
        <div
          className="absolute z-[20]"
          style={{ left: "68vw", top: "13%", width: "min(23vw, 330px)" }}
          data-anim="card"
        >
          <div className="pointer-events-auto flex items-start gap-3.5 rounded-[20px] border border-line bg-paper px-5 py-5 shadow-sm">
            <img
              src={`${A}/hero/interviewer-avatar.png`}
              alt=""
              className="h-13 w-13 shrink-0 rounded-full object-cover"
              style={{ height: "3.25rem", width: "3.25rem" }}
            />
            <p className="flex-1 pt-0.5 font-display text-[14px] font-bold leading-snug text-ink">
              How would you handle cache invalidation in a distributed system?
            </p>
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-forest">
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                aria-hidden="true"
              >
                <path
                  d="M4 15h3m3-8v16m4-12v8m4-4v0"
                  stroke="#F7F3E8"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                />
              </svg>
            </div>
          </div>
        </div>

        {/* Flow diagram — RIGHT ZONE */}
        <div
          className="absolute z-[20]"
          style={{ right: "5vw", top: "40%", width: "min(19vw, 260px)" }}
          data-anim="card"
        >
          <img
            src={`${A}/cards/flow-diagram.svg`}
            alt="System design flow: Cache to Latency and Consistency to Trade-offs"
            className="w-full"
          />
        </div>

        {/* Code card — overlaps LOWER portion of portrait */}
        <div
          className="absolute z-[20]"
          style={{ left: "43vw", bottom: "8%", width: "min(27vw, 400px)" }}
          data-anim="card"
        >
          <img
            src={`${A}/cards/code-card.svg`}
            alt="Code snippet showing interview practice code"
            className="pointer-events-auto w-full drop-shadow-sm"
          />
        </div>

        {/* Checklist — LOWER-RIGHT */}
        <div
          className="absolute z-[20]"
          style={{ right: "4vw", bottom: "9%", width: "min(18vw, 250px)" }}
          data-anim="card"
        >
          <img
            src={`${A}/cards/checklist.svg`}
            alt="Topics: System Design, Backend, Frontend, DSA, Real-World Scenarios"
            className="pointer-events-auto w-full drop-shadow-sm"
          />
        </div>

        {/* Yellow arrow square */}
        <div
          className="absolute z-[20] h-12 w-12"
          style={{ right: "3vw", bottom: "3%" }}
          data-anim="card"
        >
          <img
            src={`${A}/decorations/yellow-arrow-square.svg`}
            alt=""
            className="h-full w-full"
            aria-hidden="true"
          />
        </div>

        {/* Sticky note — between headline and portrait */}
        <div
          className="absolute z-[20] -rotate-[4deg]"
          style={{ left: "39vw", top: "47%" }}
          data-anim="annotation"
          aria-hidden="true"
        >
          <div
            className="rounded-sm px-4 py-3 shadow-[2px_3px_8px_rgba(0,0,0,0.1)]"
            style={{
              background:
                "linear-gradient(135deg, #FFF9DB 0%, #FEF3C0 50%, #FDEEA0 100%)",
              width: "165px",
            }}
          >
            <p
              className="text-[17px] leading-snug text-ink"
              style={{ fontFamily: "cursive" }}
            >
              Not just
              <br />
              questions.
              <br />
              A deeper
              <br />
              conversation.
            </p>
          </div>
        </div>
      </div>

      {/* ─── LAYER 6: Annotations (desktop) ─── */}
      <img
        src={`${A}/annotations/note-same.svg`}
        alt=""
        className="pointer-events-none absolute left-[2%] top-[5%] z-40 hidden w-[140px] -rotate-3 lg:block xl:w-[160px]"
        data-anim="annotation"
        aria-hidden="true"
      />

      <img
        src={`${A}/annotations/note-human.svg`}
        alt=""
        className="pointer-events-none absolute left-[47%] top-[3%] z-40 hidden w-[165px] -rotate-2 lg:block xl:w-[190px]"
        data-anim="annotation"
        aria-hidden="true"
      />

      <img
        src={`${A}/annotations/note-think.svg`}
        alt=""
        className="pointer-events-none absolute right-[3%] top-[5%] z-40 hidden w-[135px] rotate-[5deg] lg:block xl:w-[158px]"
        data-anim="annotation"
        aria-hidden="true"
      />

      <span
        className="pointer-events-none absolute right-[2%] top-[56%] z-40 hidden -rotate-[5deg] text-[16px] italic text-ink xl:block"
        style={{ fontFamily: "cursive" }}
        data-anim="annotation"
        aria-hidden="true"
      >
        Let&apos;s
        <br />
        go deeper.
      </span>

      {/* Star decoration */}
      <img
        src={`${A}/decorations/star.svg`}
        alt=""
        className="pointer-events-none absolute left-[3%] top-[40%] z-40 hidden w-8 opacity-50 lg:block"
        aria-hidden="true"
      />
    </section>
  );
}
