/** Only in-app destinations are ever honoured after sign-in (never an external or protocol-relative URL). */
export function safeNext(raw: string | null): string | null {
  if (!raw || !raw.startsWith('/app') || raw.startsWith('//')) return null
  return raw
}

/** The sign-in URL that returns the user to `next` afterwards. */
export const signInUrl = (next: string) => `/signin?next=${encodeURIComponent(next)}`
