import { useRef, useState } from 'react'
import { Check } from 'lucide-react'
import { InterviewerIcon } from '../../ui/interviewIcons.jsx'

const TABS = ['Questions', 'Transcript']

// The right-hand panel — built entirely from data this room actually has:
// `transcript` (this session's own answered turns, accumulated in
// Interview.jsx as each answer is really submitted — never fetched, never
// invented) plus the current, in-progress question/answer. Nothing here
// renders a question that hasn't really been asked yet, and there is no
// third "Notes" tab because no notes feature exists.
function TranscriptPanel({
  transcript,
  currentQuestionText,
  earlierAnswersCount = 0,
  className = '',
}) {
  const [activeTab, setActiveTab] = useState(TABS[0])
  const tabRefs = useRef([])
  const hasCurrentQuestion = Boolean(currentQuestionText)

  // ARIA tabs pattern: Left/Right moves between the two real tabs.
  function handleTabKeyDown(event, index) {
    if (event.key !== 'ArrowRight' && event.key !== 'ArrowLeft') return
    event.preventDefault()
    const nextIndex = (index + (event.key === 'ArrowRight' ? 1 : -1) + TABS.length) % TABS.length
    setActiveTab(TABS[nextIndex])
    tabRefs.current[nextIndex]?.focus()
  }

  return (
    <div
      className={`flex flex-col gap-3 rounded-[var(--radius-panel)] border border-glass/70 bg-glass/50 p-3 lg:max-h-full lg:min-h-0 ${className}`}
    >
      <div role="tablist" aria-label="Interview panel" className="flex shrink-0 rounded-2xl bg-primary-light-2 p-1">
        {TABS.map((tab, index) => (
          <button
            key={tab}
            ref={(node) => {
              tabRefs.current[index] = node
            }}
            id={`interview-tab-${tab}`}
            type="button"
            role="tab"
            aria-selected={activeTab === tab}
            aria-controls="interview-tabpanel"
            tabIndex={activeTab === tab ? 0 : -1}
            onClick={() => setActiveTab(tab)}
            onKeyDown={(event) => handleTabKeyDown(event, index)}
            className={`flex-1 rounded-xl px-3 py-2 text-sm font-medium transition-colors duration-200 ${
              activeTab === tab ? 'bg-glass text-primary shadow-glass-sm' : 'text-muted hover:text-ink'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      <div
        id="interview-tabpanel"
        role="tabpanel"
        aria-labelledby={`interview-tab-${activeTab}`}
        className="flex flex-col gap-2 px-1 pb-1 lg:min-h-0 lg:flex-1 lg:overflow-y-auto"
      >
        {/* GET /interviews/{id} doesn't return earlier turns, so after a
            refresh/resume the answers given before this page loaded can't
            be listed here — say so rather than implying they never
            happened. */}
        {earlierAnswersCount > 0 && (
          <p className="px-2 pb-1 text-xs leading-relaxed text-muted">
            {earlierAnswersCount === 1
              ? '1 earlier answer is saved but not shown here after reloading.'
              : `${earlierAnswersCount} earlier answers are saved but not shown here after reloading.`}
          </p>
        )}
        {activeTab === 'Questions' ? (
          <ol className="flex flex-col">
            {/* Compact rows: number, one line of question, state. Numbers
                are exact even after a resume — they start after the
                earlier answers the API reports (earlierAnswersCount). */}
            {transcript.map((entry, index) => (
              <li key={entry.questionId} className="flex items-center gap-3 rounded-lg px-2 py-2">
                <span className="w-5 shrink-0 text-center text-xs font-semibold tabular-nums text-muted">
                  {earlierAnswersCount + index + 1}
                </span>
                <p className="min-w-0 flex-1 truncate text-sm text-ink/75">{entry.questionText}</p>
                <Check className="h-4 w-4 shrink-0 text-success" strokeWidth={2.25} aria-hidden="true" />
                <span className="sr-only">answered</span>
              </li>
            ))}
            {hasCurrentQuestion && (
              <li aria-current="step" className="flex items-center gap-3 rounded-lg bg-primary-light/60 px-2 py-2">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary text-[11px] font-semibold tabular-nums text-white">
                  {earlierAnswersCount + transcript.length + 1}
                </span>
                {/* The full question is already the focal point of the main
                    column — this row only marks which one is active rather
                    than repeating its text a second time on screen. */}
                <p className="min-w-0 flex-1 truncate text-sm font-semibold text-primary">Current question</p>
                <span aria-hidden="true" className="h-2 w-2 shrink-0 rounded-full bg-primary" />
              </li>
            )}
          </ol>
        ) : (
          <div className="flex flex-col gap-4">
            {transcript.length === 0 && !hasCurrentQuestion && (
              <p className="text-sm text-muted">Your transcript will appear here as the interview progresses.</p>
            )}
            {transcript.map((entry) => (
              <div key={entry.questionId} className="flex flex-col gap-2">
                <TranscriptMessage speaker="interviewer" text={entry.questionText} />
                <TranscriptMessage speaker="candidate" text={entry.answer} />
              </div>
            ))}
            {hasCurrentQuestion && (
              <div className="flex flex-col gap-2">
                {/* The candidate's own live answer is never duplicated here
                    — it appears exactly once, in the live-transcript strip
                    above the voice dock while speaking, then once more,
                    finalized, in this same list once Finish Answer actually
                    submits it (as one of the `transcript.map` entries
                    above). */}
                <TranscriptMessage speaker="interviewer" text={currentQuestionText} emphasized />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// An interview transcript entry, not a chat bubble — plain identity +
// text, no message-app chrome (timestamps, tails, alternating alignment).
function TranscriptMessage({ speaker, text, emphasized = false }) {
  const isInterviewer = speaker === 'interviewer'

  return (
    <div className={`flex items-start gap-2.5 ${emphasized ? '' : 'opacity-70'}`}>
      {isInterviewer ? (
        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary-light text-primary">
          <InterviewerIcon className="h-3.5 w-3.5" />
        </span>
      ) : (
        <span className="h-6 w-6 shrink-0 overflow-hidden rounded-full">
          <img src="/assets/people/candidate.webp" alt="" className="h-full w-full object-cover object-top" />
        </span>
      )}
      <div className="min-w-0">
        <p className="text-xs font-semibold text-ink">{isInterviewer ? 'AI Interviewer' : 'You'}</p>
        <p className="text-sm leading-relaxed text-ink">{text}</p>
      </div>
    </div>
  )
}

export default TranscriptPanel
