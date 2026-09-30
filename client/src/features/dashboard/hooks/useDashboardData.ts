import { useCallback, useEffect, useState } from 'react'
import { ApiError } from '@/lib/api'
import { getCurrentUser } from '@/lib/auth'
import { fetchDashboard } from '../api/dashboardApi'
import type { DashboardView } from '../data/dashboardViewModel'
import { mapDashboard } from '../lib/dashboardMapper'

export type DashboardState =
  | { status: 'loading' }
  | { status: 'ready'; view: DashboardView }
  | { status: 'unauthenticated' }
  | { status: 'error' }

async function load(): Promise<DashboardState> {
  try {
    // The session is an HttpOnly cookie: requests just include credentials. `/auth/me` only supplies the display name.
    const [dashboard, user] = await Promise.all([fetchDashboard(), getCurrentUser().catch(() => null)])
    return { status: 'ready', view: mapDashboard(dashboard, user) }
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return { status: 'unauthenticated' }
    return { status: 'error' } // network failure, 5xx, anything unexpected: generic, retryable
  }
}

// Shared in-flight request: React StrictMode mounts effects twice in development, and
// both runs reuse this one request instead of sending two.
let inflight: Promise<DashboardState> | null = null
function loadOnce(): Promise<DashboardState> {
  inflight ??= load().finally(() => {
    inflight = null
  })
  return inflight
}

export function useDashboardData() {
  const [state, setState] = useState<DashboardState>({ status: 'loading' })

  useEffect(() => {
    let cancelled = false
    void loadOnce().then((result) => {
      if (!cancelled) setState(result)
    })
    return () => {
      cancelled = true
    }
  }, [])

  const retry = useCallback(() => {
    setState({ status: 'loading' })
    void loadOnce().then(setState)
  }, [])

  return { state, retry }
}
