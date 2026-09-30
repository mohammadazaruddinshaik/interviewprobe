const pulse = 'animate-pulse rounded-2xl bg-ink/[0.07] motion-reduce:animate-none'

/** Layout-preserving placeholder while the interview state loads. */
function RoomSkeleton() {
  return (
    <div role="status" aria-label="Loading interview" className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_280px] xl:grid-cols-[minmax(0,1fr)_320px]">
      <div className="flex flex-col gap-6">
        <div className={`h-[148px] ${pulse}`} />
        <div className={`h-[260px] ${pulse}`} />
      </div>
      <div className={`h-[220px] max-lg:hidden ${pulse}`} />
    </div>
  )
}

export default RoomSkeleton
