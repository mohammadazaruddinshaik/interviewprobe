interface RoomHeaderProps {
  roleLabel: string
  difficultyLabel: string
  current: number
  total: number
  onEnd: () => void
  endDisabled: boolean
}

function RoomHeader({ roleLabel, difficultyLabel, current, total, onEnd, endDisabled }: RoomHeaderProps) {
  return (
    <header data-room="header">
      <div className="flex items-center justify-between gap-4">
        <a
          href="/app"
          className="group -ml-1 inline-flex items-center gap-2 rounded-lg px-1 py-1.5 text-[13.5px] font-semibold text-forest outline-offset-2 focus-visible:outline-[3px] focus-visible:outline-yellow"
        >
          <span aria-hidden="true" className="transition-transform duration-200 group-hover:-translate-x-[3px] motion-reduce:transition-none">←</span>
          Dashboard
        </a>
        {/* Deliberately quiet: secondary to answering. */}
        <button
          type="button"
          onClick={onEnd}
          disabled={endDisabled}
          className="rounded-lg px-2.5 py-1.5 text-[13px] font-medium text-ink/60 outline-offset-2 transition-colors duration-200 hover:text-deep focus-visible:outline-[3px] focus-visible:outline-yellow disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:transition-none"
        >
          End interview
        </button>
      </div>

      <div className="mt-5 flex flex-wrap items-center justify-between gap-x-6 gap-y-3">
        <p className="flex items-center gap-2.5 text-[11px] font-semibold tracking-[0.18em] text-ink/45">
          <span aria-hidden="true" className="h-2 w-2 rounded-[2px] bg-yellow" />
          {roleLabel.toUpperCase()} · {difficultyLabel.toUpperCase()}
        </p>
        <div className="flex items-center gap-3">
          <span aria-hidden="true" className="flex gap-1">
            {Array.from({ length: total }, (_, i) => (
              <i key={i} className={`h-[5px] w-4 rounded-[3px] ${i + 1 < current ? 'bg-forest' : i + 1 === current ? 'bg-yellow' : 'bg-forest/[0.12]'}`} />
            ))}
          </span>
          <span className="text-[13px] font-semibold text-deep">
            Question {current} <span className="font-medium text-ink/55">of {total}</span>
          </span>
        </div>
      </div>
    </header>
  )
}

export default RoomHeader
