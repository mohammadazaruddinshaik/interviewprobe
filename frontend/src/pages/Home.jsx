import Footer from '../components/layout/Footer.jsx'
import FeatureCardGrid from '../components/landing/FeatureCardGrid.jsx'
import FeatureStrip from '../components/landing/FeatureStrip.jsx'
import GlassShell from '../components/landing/GlassShell.jsx'
import HeroSection from '../components/landing/HeroSection.jsx'
import LandingNavbar from '../components/landing/LandingNavbar.jsx'
import TrustSection from '../components/landing/TrustSection.jsx'

function Home() {
  return (
    <div className="text-ink">
      <div className="px-3 py-3 sm:px-5 sm:py-5 lg:px-8 lg:py-6">
        <GlassShell>
          <LandingNavbar />
          <HeroSection />
          <FeatureStrip />
          <TrustSection />
          <FeatureCardGrid />
        </GlassShell>
      </div>
      <Footer />
    </div>
  )
}

export default Home
