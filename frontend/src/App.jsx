import { Route, Routes } from 'react-router-dom'
import Home from './pages/Home.jsx'
import Interview from './pages/Interview.jsx'
import InterviewNew from './pages/InterviewNew.jsx'
import InterviewResult from './pages/InterviewResult.jsx'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/interview/new" element={<InterviewNew />} />
      <Route path="/interview/:sessionId" element={<Interview />} />
      <Route path="/interview/:sessionId/result" element={<InterviewResult />} />
    </Routes>
  )
}

export default App
