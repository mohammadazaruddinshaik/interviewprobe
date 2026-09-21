import QuestionSpeaker from './QuestionSpeaker.jsx'

function QuestionPanel({
  questionNumber,
  text,
  headingRef,
  speakerDisabled,
  isSpeaking,
  speakerHasError,
  speakerSupported,
  onReplay,
  onStopSpeaking,
}) {
  return (
    <section className="motion-safe:animate-rise mx-auto max-w-3xl px-6 pb-4 pt-14 text-center sm:px-8">
      <div className="flex items-center justify-center gap-2">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted">
          Question {questionNumber}
        </p>
        <QuestionSpeaker
          text={text}
          disabled={speakerDisabled}
          isSpeaking={isSpeaking}
          hasError={speakerHasError}
          supported={speakerSupported}
          onReplay={onReplay}
          onStop={onStopSpeaking}
        />
      </div>
      <h1
        ref={headingRef}
        tabIndex={-1}
        className="mt-4 rounded-lg text-2xl font-semibold leading-snug text-ink focus:outline focus:outline-2 focus:outline-accent focus:outline-offset-4 sm:text-3xl"
      >
        {text}
      </h1>
    </section>
  )
}

export default QuestionPanel
