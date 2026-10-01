const bar = 'animate-pulse rounded-md bg-cream/[0.08] motion-reduce:animate-none'

/** Mirrors the voice room's geometry (header, presence, question lines, primary control) so nothing jumps on load. */
function RoomSkeleton() {
  return (
    <div role="status" aria-label="Loading interview" className="relative min-h-[100dvh] bg-[#06110a]">
      <div aria-hidden="true">
        <div className="mx-auto flex h-14 max-w-[1100px] items-center justify-between px-4 sm:px-6">
          <div className={`h-4 w-32 ${bar}`} />
          <div className={`h-4 w-40 ${bar}`} />
        </div>
        <div className="mx-auto flex max-w-[760px] flex-col items-center px-5 pt-8">
          <div className="size-[184px] animate-pulse rounded-full bg-cream/[0.06] motion-reduce:animate-none sm:size-[232px]" />
          <div className="mt-10 flex w-full flex-col items-center gap-3">
            <div className={`h-3 w-24 ${bar}`} />
            <div className={`h-7 w-full sm:h-8 ${bar}`} />
            <div className={`h-7 w-[78%] sm:h-8 ${bar}`} />
          </div>
          <div className={`mt-10 h-[54px] w-44 rounded-xl ${bar}`} />
        </div>
      </div>
    </div>
  )
}

export default RoomSkeleton
