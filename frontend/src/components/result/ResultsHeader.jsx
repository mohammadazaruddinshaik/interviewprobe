import { ArrowLeft } from 'lucide-react'
import { Link } from 'react-router-dom'
import Button from '../ui/Button.jsx'

// The page's own title row. The back control is a real destination (Home)
// rather than a browser-history "go back" — there is no reliable prior
// page to return to (a shared link, a bookmark, a refresh), so it never
// pretends to be anything other than what it actually does. This is also
// the page's only "Back to home" control — see Interview.lifecycle's
// established pattern of keeping exactly one link per real destination
// rather than repeating it in a footer too.
//
// "Practice Again" is the one real, working action this header exposes —
// it reuses the existing interview-creation flow (the same route Setup's
// own "Get Started" uses). The reference also shows "Share Result" and
// "Download Report", but neither has a real implementation anywhere in
// this product, so they're left out entirely rather than becoming dead
// buttons.
function ResultsHeader() {
  return (
    <div className="flex flex-col gap-4 px-4 pt-2 sm:px-6 sm:pt-3 lg:flex-row lg:items-start lg:justify-between lg:px-8">
      <div className="flex items-start gap-3 sm:gap-4">
        <Link
          to="/"
          aria-label="Back to home"
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-glass/70 bg-glass/60 text-ink transition-colors duration-200 hover:bg-glass sm:h-11 sm:w-11 xl:mt-1 xl:h-12 xl:w-12"
        >
          <ArrowLeft className="h-4.5 w-4.5" strokeWidth={1.75} />
        </Link>
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink sm:text-3xl xl:text-[2.5rem] xl:leading-tight">Interview Results</h1>
          <p className="mt-1 max-w-2xl text-sm leading-relaxed text-muted xl:text-base">
            Here&apos;s a detailed analysis of your interview performance with personalized feedback.
          </p>
        </div>
      </div>

      <Button to="/interview/new" variant="primary" withArrow className="shrink-0 self-start lg:mt-1">
        Practice again
      </Button>
    </div>
  )
}

export default ResultsHeader
