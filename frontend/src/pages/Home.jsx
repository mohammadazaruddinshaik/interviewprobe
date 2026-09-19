import Footer from '../components/layout/Footer.jsx'
import Navbar from '../components/layout/Navbar.jsx'
import FeatureStrip from '../components/home/FeatureStrip.jsx'
import FinalCTA from '../components/home/FinalCTA.jsx'
import Hero from '../components/home/Hero.jsx'
import HowItWorks from '../components/home/HowItWorks.jsx'
import Roles from '../components/home/Roles.jsx'
import StudentSection from '../components/home/StudentSection.jsx'

function Home() {
  return (
    <div className="bg-cream text-ink">
      <Navbar />
      <main>
        <Hero />
        <FeatureStrip />
        <HowItWorks />
        <Roles />
        <StudentSection />
        <FinalCTA />
      </main>
      <Footer />
    </div>
  )
}

export default Home
