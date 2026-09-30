import type { ReactNode } from 'react'

/**
 * Loading placeholder that keeps the exact box of representative content:
 * the text stays in layout but is transparent, so nothing jumps when real data arrives.
 */
function Skeleton({ children }: { children: ReactNode }) {
  return (
    <span aria-hidden="true" className="inline-block animate-pulse select-none rounded-md bg-ink/[0.08] text-transparent motion-reduce:animate-none">
      {children}
    </span>
  )
}

export default Skeleton
