import { LearningIcon } from '../ui/interviewIcons.jsx'

// The reference's "What's Next?" section offers three tiles (Practice
// Again, Explore Topics, Track Progress), but only Practice Again is a
// real, working destination in this product — there is no topic-browsing
// or progress-history page to link to (see App.jsx's router). Rather than
// pad the section with dead tiles, or repeat the "Practice again" button
// ResultsHeader already renders (which would leave two controls with the
// same name on one page), this stays a short, honest closing note.
function NextSteps() {
  return (
    <div className="flex items-center gap-4 rounded-[22px] border border-glass/70 bg-glass/50 p-5 sm:p-6">
      <LearningIcon className="h-6 w-6 shrink-0 text-primary" />
      <div>
        <h2 className="text-base font-semibold text-ink">What&apos;s Next?</h2>
        <p className="mt-1 text-sm leading-relaxed text-muted">
          Use the <span className="font-medium text-ink">Practice again</span> button above to start a new interview
          with different questions whenever you&apos;re ready.
        </p>
      </div>
    </div>
  )
}

export default NextSteps
