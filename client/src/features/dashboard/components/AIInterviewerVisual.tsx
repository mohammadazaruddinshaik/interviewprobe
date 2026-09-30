/**
 * Compact "interview conversation" scene: question -> answer -> deeper probe.
 * Pure UI/CSS (no asset). The three steps are marked data-dash="vis-*" so the
 * dashboard entrance can reveal them in order.
 */
function AIInterviewerVisual() {
  return (
    <figure
      aria-label="AI interviewer conversation preview"
      className="relative m-0 flex flex-col justify-center gap-2 overflow-hidden rounded-xl border border-forest/10 bg-forest/[0.04] p-3 @[620px]:gap-3.5 @[620px]:p-4"
    >
      {/* Thin rail linking the three steps */}
      <span aria-hidden="true" className="absolute bottom-7 left-[22px] top-7 w-px bg-forest/15 @[460px]:left-[26px]" />

      <div data-dash="vis-q" className="relative pl-6 @[460px]:pl-7">
        <span aria-hidden="true" className="absolute left-[3px] top-[14px] h-2.5 w-2.5 rounded-full border-[1.5px] border-forest/60 bg-cream @[460px]:left-[5px]" />
        <div className="rounded-lg border border-ink/10 bg-white/85 px-3 py-2 @[620px]:py-2.5 shadow-[0_6px_16px_-12px_rgb(20_42_11/0.35)]">
          <p className="text-[9.5px] font-semibold tracking-[0.14em] text-ink/45">INTERVIEWER</p>
          <p className="mt-0.5 font-serif text-[12.5px] leading-[1.3] @[620px]:mt-1 text-deep">
            “How would you design the retrieval layer for a RAG system?”
          </p>
        </div>
      </div>

      <div data-dash="vis-a" className="relative pl-6 @[460px]:pl-7">
        <span aria-hidden="true" className="absolute left-[3px] top-[14px] h-2.5 w-2.5 rounded-full bg-forest/70 @[460px]:left-[5px]" />
        <div className="rounded-lg border border-forest/10 bg-forest/[0.07] px-3 py-2 @[620px]:py-2.5">
          <p className="text-[9.5px] font-semibold tracking-[0.14em] text-ink/45">YOU</p>
          <p className="mt-0.5 text-[12px] leading-[1.35] @[620px]:mt-1 text-ink/70">
            “Use vector search with metadata filtering and reranking.”
          </p>
        </div>
      </div>

      <div data-dash="vis-p" className="relative pl-6 @[460px]:pl-7">
        <span aria-hidden="true" className="absolute left-[2px] top-[13px] h-3 w-3 rounded-full border-2 border-yellow bg-forest ring-4 ring-yellow/30 @[460px]:left-[4px]" />
        <div className="rounded-lg border border-yellow bg-yellow/25 px-3 py-2 @[620px]:py-2.5 shadow-[0_8px_18px_-12px_rgb(20_42_11/0.4)]">
          <p className="flex items-center gap-1.5 text-[9.5px] font-semibold tracking-[0.14em] text-deep/70">
            <span aria-hidden="true" className="h-1.5 w-1.5 rounded-[2px] bg-forest" />
            AI PROBE
          </p>
          <p className="mt-0.5 font-serif text-[12.5px] font-medium leading-[1.3] @[620px]:mt-1 text-deep">
            “What was your strategy for handling stale embeddings?”
          </p>
        </div>
      </div>
    </figure>
  )
}

export default AIInterviewerVisual
