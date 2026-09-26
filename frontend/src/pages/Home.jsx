import Footer from '../components/layout/Footer.jsx'
import Navbar from '../components/layout/Navbar.jsx'
import AdaptiveInterviewSection from '../components/home/AdaptiveInterviewSection.jsx'
import EvaluationSection from '../components/home/EvaluationSection.jsx'
import FeatureStrip from '../components/home/FeatureStrip.jsx'
import FinalCTA from '../components/home/FinalCTA.jsx'
import Hero from '../components/home/Hero.jsx'
import Roles from '../components/home/Roles.jsx'
import VoiceFirstSection from '../components/home/VoiceFirstSection.jsx'

function Home() {
  return (
    <div className="text-ink">
      <Navbar />
      <main>
        <Hero />
        <FeatureStrip />
        <AdaptiveInterviewSection />
        <VoiceFirstSection />
        <EvaluationSection />
        <Roles />
        <FinalCTA />
      </main>
      <Footer />
    </div>
  )
}

export default Home
