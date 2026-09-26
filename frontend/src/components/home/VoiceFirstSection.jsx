import GlassCard from '../ui/GlassCard.jsx'
import SectionHeading from '../ui/SectionHeading.jsx'
import { MicIcon, SpeakerIcon } from '../ui/icons.jsx'

// Describes the real voice pipeline (Azure Speech for TTS, Deepgram for
// STT — see README's "Voice architecture") in plain product language.
function VoiceFirstSection() {
  return (
    <section className="px-6 py-20">
      <div className="mx-auto grid max-w-7xl gap-14 lg:grid-cols-2 lg:items-center lg:gap-16">
        <GlassCard className="order-2 flex flex-col gap-4 p-6 sm:p-8 lg:order-1">
          <div className="flex items-center gap-3 rounded-2xl bg-white/70 p-4">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary text-white">
              <SpeakerIcon className="h-4.5 w-4.5" />
            </span>
            <div>
              <p className="text-sm font-semibold text-ink">The interviewer speaks</p>
              <p className="text-xs text-muted">Every question is read aloud, naturally.</p>
            </div>
          </div>

          <div className="flex items-center gap-3 rounded-2xl bg-white/70 p-4">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary text-white">
              <MicIcon className="h-4.5 w-4.5" />
            </span>
            <div className="flex-1">
              <p className="text-sm font-semibold text-ink">You answer by talking</p>
              <p className="text-xs text-muted">Your words appear live as you speak.</p>
            </div>
            <span className="flex items-end gap-0.5" aria-hidden="true">
              {[6, 12, 9, 15, 7].map((height, index) => (
                <span
                  key={index}
                  className="w-1 rounded-full bg-primary/60"
                  style={{ height: `${height}px` }}
                />
              ))}
            </span>
          </div>
        </GlassCard>

        <SectionHeading
          className="order-1 lg:order-2"
          eyebrow="Voice-First Experience"
          title="Talk through it, the way a real interview actually feels."
          description="No typing under pressure. The AI interviewer speaks every question aloud and listens to your spoken answer in real time, so practicing feels like the conversation it's meant to be."
        />
      </div>
    </section>
  )
}

export default VoiceFirstSection
