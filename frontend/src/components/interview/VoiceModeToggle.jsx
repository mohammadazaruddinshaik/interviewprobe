import { HeadsetIcon } from '../ui/icons.jsx'

// Purely a UI switch: reports on/off to the caller and knows nothing about
// speech, sessions, or the API. Interview.jsx owns what "on" actually does.
function VoiceModeToggle({ enabled, onToggle }) {
  return (
    <div className="mx-auto flex max-w-3xl flex-col items-center gap-1.5 px-6 pt-8 sm:px-8">
      <button
        type="button"
        onClick={() => onToggle(!enabled)}
        aria-pressed={enabled}
        aria-describedby="voice-mode-description"
        className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium transition-colors duration-200 ${
          enabled
            ? 'border-accent/40 bg-accent-soft text-accent'
            : 'border-line bg-white/70 text-ink hover:border-ink/30 hover:bg-white'
        }`}
      >
        <HeadsetIcon className="h-4 w-4" />
        {enabled ? 'Voice mode: on' : 'Voice mode: off'}
      </button>
      <p id="voice-mode-description" className="text-center text-xs text-muted">
        {enabled
          ? 'Questions are read aloud automatically. You still choose when to speak your answer.'
          : 'Turn on to have each question read aloud automatically.'}
      </p>
    </div>
  )
}

export default VoiceModeToggle
