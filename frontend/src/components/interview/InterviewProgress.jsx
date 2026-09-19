function InterviewProgress({ current, total, className = '' }) {
  return (
    <div
      role="img"
      aria-label={`Question ${current} of ${total}`}
      className={`flex items-center gap-1.5 ${className}`}
    >
      {Array.from({ length: total }, (_, index) => (
        <span
          key={index}
          aria-hidden="true"
          className={`h-1.5 w-1.5 rounded-full transition-colors duration-200 ${
            index < current ? 'bg-accent' : 'bg-line'
          }`}
        />
      ))}
    </div>
  )
}

export default InterviewProgress
