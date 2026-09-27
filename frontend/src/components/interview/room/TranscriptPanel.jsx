import { useState } from 'react'
import { Check } from 'lucide-react'
import { NeuralChipIcon } from '../../ui/interviewIcons.jsx'

const TABS = ['Questions', 'Transcript']

// The right-hand panel — built entirely from data this room actually has:
// `transcript` (this session's own answered turns, accumulated in
// Interview.jsx as each answer is really submitted — never fetched, never
// invented) plus the current, in-progress question/answer. Nothing here
// renders a question that hasn't really been asked yet, and there is no
// third "Notes" tab because no notes feature exists.
function TranscriptPanel({ transcript, currentQuestionText, currentAnswer, interimTranscript, className = '' }) {
  const [activeTab, setActiveTab] = useState(TABS[0])
  const hasCurrentQuestion = Boolean(currentQuestionText)

  return (
    <div className={`flex flex-col gap-3 ${className}`}>
      <div role="tablist" aria-label="Interview panel" className="flex rounded-full border border-line bg-glass/50 p-1">
        {TABS.map((tab) => (
          <button
            key={tab}
            type="button"
            role="tab"
            aria-selected={activeTab === tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 rounded-full px-3 py-1.5 text-sm font-medium transition-colors duration-200 ${
              activeTab === tab ? 'bg-glass text-primary shadow-glass-sm' : 'text-muted hover:text-ink'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      <div className="flex flex-col gap-2 rounded-[22px] border border-glass/70 bg-glass/60 p-4 shadow-glass-sm">
        {activeTab === 'Questions' ? (
          <ol className="flex flex-col gap-1">
            {transcript.map((entry, index) => (
              <li key={entry.questionId} className="flex items-start gap-2.5 rounded-lg px-2 py-2">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-success/15 text-success">
                  <Check className="h-3 w-3" strokeWidth={2.5} />
                </span>
                <p className="truncate text-sm text-muted">{entry.questionText}</p>
                <span className="sr-only">Question {index + 1}, answered</span>
              </li>
            ))}
            {hasCurrentQuestion && (
              <li className="flex items-start gap-2.5 rounded-lg bg-primary-light/40 px-2 py-2">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary text-[10px] font-bold text-white">
                  {transcript.length + 1}
                </span>
                {/* The full question is already the focal point of the main
                    panel — this row only needs to say which one is active,
                    not repeat its exact text a second time on screen. */}
                <p className="text-sm font-medium text-ink">Current question</p>
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
                <TranscriptMessage speaker="interviewer" text={currentQuestionText} emphasized />
                {(currentAnswer || interimTranscript) && (
                  <TranscriptMessage speaker="candidate" text={currentAnswer || interimTranscript} emphasized live />
                )}
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
function TranscriptMessage({ speaker, text, emphasized = false, live = false }) {
  const isInterviewer = speaker === 'interviewer'

  return (
    <div className={`flex items-start gap-2.5 ${emphasized ? '' : 'opacity-70'}`}>
      {isInterviewer ? (
        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary-light text-primary">
          <NeuralChipIcon className="h-3.5 w-3.5" />
        </span>
      ) : (
        <span className="h-6 w-6 shrink-0 overflow-hidden rounded-full">
          <img src="/assets/people/candidate.webp" alt="" className="h-full w-full object-cover object-top" />
        </span>
      )}
      <div className="min-w-0">
        <p className="text-xs font-semibold text-ink">{isInterviewer ? 'AI Interviewer' : 'You'}</p>
        <p className="text-sm leading-relaxed text-ink">
          {text}
          {live && (
            <span aria-hidden="true" className="motion-safe:animate-pulse">
              …
            </span>
          )}
        </p>
      </div>
    </div>
  )
}

export default TranscriptPanel
