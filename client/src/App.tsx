import Navigation from '@/features/landing/components/Navigation'
import Hero from '@/features/landing/components/Hero'
import FeaturesSection from '@/features/landing/components/FeaturesSection'
import Footer from '@/features/landing/components/Footer'
import { useLandingAnimations } from '@/hooks/useLandingAnimations'

function App() {
  const scope = useLandingAnimations<HTMLDivElement>()

  return (
    <div ref={scope} className="min-h-screen bg-cream text-ink">
      <Navigation />
      <Hero />
      <FeaturesSection />
      <Footer />
    </div>
  )
}

export default App
