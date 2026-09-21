function InterviewerIdentity({ name, role }) {
  return (
    <div className="text-center">
      <p className="text-lg font-semibold text-ink">{name}</p>
      <p className="text-sm text-muted">{role}</p>
    </div>
  )
}

export default InterviewerIdentity
