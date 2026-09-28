import Footer from '../components/layout/Footer.jsx'
import FeatureStrip from '../components/landing/FeatureStrip.jsx'
import HeroSection from '../components/landing/HeroSection.jsx'
import LandingBackdrop from '../components/landing/LandingBackdrop.jsx'
import LandingNavbar from '../components/landing/LandingNavbar.jsx'
import WhySection from '../components/landing/WhySection.jsx'

// Landing sits directly on the open backdrop (floating navbar, arcs,
// dotted fields), not inside one boxed shell — the master reference's
// composition. Five parts only: navbar, hero, capability band, why, footer.
function Home() {
  return (
    <div className="relative isolate min-h-screen text-ink">
      <LandingBackdrop />
      <LandingNavbar />
      <main>
        <HeroSection />
        <FeatureStrip />
        <WhySection />
      </main>
      <Footer />
    </div>
  )
}

export default Home
