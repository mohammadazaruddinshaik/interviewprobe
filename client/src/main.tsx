import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@/styles/index.css'
import App from '@/App.tsx'
import Dashboard from '@/features/dashboard/components/Dashboard.tsx'
import SignInPage from '@/features/auth/components/SignInPage.tsx'
import InterviewSetupPage from '@/features/interview-setup/components/InterviewSetupPage.tsx'
import InterviewRoomPage from '@/features/interview/components/InterviewRoomPage.tsx'
import ResultPage from '@/features/result/components/ResultPage.tsx'

// Minimal path-based routing: "/" (and any unknown path) is the landing page, "/app" is the
// product dashboard, "/signin" is Google sign-in, "/app/interviews/new" is interview setup, "/app/interviews/:id" is the interview room, "/app/interviews/:id/result" is the result page.
function resolveRoute() {
  const path = window.location.pathname.replace(/\/+$/, '')
  if (path === '/signin') return <SignInPage />
  if (path === '/app') return <Dashboard />
  if (path === '/app/interviews/new') return <InterviewSetupPage />
  const result = /^\/app\/interviews\/([^/]+)\/result$/.exec(path)
  if (result) return <ResultPage key={result[1]} interviewId={decodeURIComponent(result[1])} />
  const room = /^\/app\/interviews\/([^/]+)$/.exec(path)
  if (room) return <InterviewRoomPage key={room[1]} interviewId={decodeURIComponent(room[1])} />
  return <App />
}

createRoot(document.getElementById('root')!).render(<StrictMode>{resolveRoute()}</StrictMode>)
