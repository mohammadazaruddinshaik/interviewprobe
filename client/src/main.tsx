import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@/styles/index.css'
import App from '@/App.tsx'
import Dashboard from '@/features/dashboard/components/Dashboard.tsx'
import ResultsPage from '@/features/dashboard/components/ResultsPage.tsx'
import SignInPage from '@/features/auth/components/SignInPage.tsx'
import RequireAuth from '@/features/auth/components/RequireAuth.tsx'
import NotFoundPage from '@/features/app/components/NotFoundPage.tsx'
import InterviewSetupPage from '@/features/interview-setup/components/InterviewSetupPage.tsx'
import InterviewRoomPage from '@/features/interview/components/InterviewRoomPage.tsx'
import ResultPage from '@/features/result/components/ResultPage.tsx'

// Minimal path-based routing.
//   public:        "/" landing, "/signin" Google sign-in
//   authenticated: "/app" dashboard, "/app/results" recent results, "/app/interviews/new" setup, "/app/interviews/:id" room,
//                  "/app/interviews/:id/result" result (every /app route is behind RequireAuth)
//   anything else: not found
function resolveRoute() {
  const path = window.location.pathname.replace(/\/+$/, '') || '/'
  if (path === '/') return <App />
  if (path === '/signin') return <SignInPage />
  if (path === '/app') return <RequireAuth><Dashboard /></RequireAuth>
  if (path === '/app/results') return <RequireAuth><ResultsPage /></RequireAuth>
  if (path === '/app/interviews/new') return <RequireAuth><InterviewSetupPage /></RequireAuth>
  const result = /^\/app\/interviews\/([^/]+)\/result$/.exec(path)
  if (result) return <RequireAuth><ResultPage key={result[1]} interviewId={decodeURIComponent(result[1])} /></RequireAuth>
  const room = /^\/app\/interviews\/([^/]+)$/.exec(path)
  if (room) return <RequireAuth><InterviewRoomPage key={room[1]} interviewId={decodeURIComponent(room[1])} /></RequireAuth>
  return <NotFoundPage />
}

createRoot(document.getElementById('root')!).render(<StrictMode>{resolveRoute()}</StrictMode>)
