/** A neutral placeholder block. No representative or fake data is shown while loading. */
function Skeleton({ className }: { className: string }) {
  return <div aria-hidden="true" className={`animate-pulse rounded-lg bg-ink/[0.07] motion-reduce:animate-none ${className}`} />
}

export default Skeleton
