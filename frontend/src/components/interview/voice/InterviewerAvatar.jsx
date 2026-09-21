// A plain initials badge — deliberately not a generated face or stock
// photo. `isSpeaking` only adds a static ring (no motion of its own); the
// actual speaking cue is SpeakingIndicator, kept separate so this stays a
// dumb, reusable presentational piece.
function InterviewerAvatar({ initials, isSpeaking }) {
  return (
    <div
      aria-hidden="true"
      className={`flex h-20 w-20 shrink-0 items-center justify-center rounded-full border bg-accent-soft text-xl font-semibold text-accent transition-colors duration-200 sm:h-24 sm:w-24 sm:text-2xl ${
        isSpeaking ? 'border-accent/60' : 'border-accent/25'
      }`}
    >
      {initials}
    </div>
  )
}

export default InterviewerAvatar
