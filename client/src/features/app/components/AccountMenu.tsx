import { useEffect, useRef, useState } from 'react'
import { ChevronDown, LogOut } from 'lucide-react'
import { logout, type AuthUser } from '@/lib/auth'
import { APP_NAV } from '../lib/nav'

const initialsOf = (name: string) =>
  name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join('') || '?'

function Avatar({ user, size }: { user: AuthUser; size: string }) {
  const [broken, setBroken] = useState(false)
  if (user.avatar_url && !broken) {
    return <img src={user.avatar_url} alt="" referrerPolicy="no-referrer" onError={() => setBroken(true)} className={`${size} rounded-full object-cover`} />
  }
  return (
    <span aria-hidden="true" className={`${size} flex items-center justify-center rounded-full bg-yellow text-[12px] font-bold text-ink`}>
      {initialsOf(user.name)}
    </span>
  )
}

/** The signed-in user's control: identity, the app's pages, and logout (the existing server logout). */
function AccountMenu({ user, active }: { user: AuthUser; active: string }) {
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [failed, setFailed] = useState(false)
  const root = useRef<HTMLDivElement>(null)
  const trigger = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!open) return
    const onPointer = (event: PointerEvent) => {
      if (root.current && !root.current.contains(event.target as Node)) setOpen(false)
    }
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false)
        trigger.current?.focus()
      }
    }
    document.addEventListener('pointerdown', onPointer)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('pointerdown', onPointer)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  const signOut = async () => {
    if (busy) return
    setBusy(true)
    setFailed(false)
    try {
      await logout()
      window.location.assign('/')
    } catch {
      setFailed(true)
      setBusy(false)
    }
  }

  const item =
    'flex min-h-10 w-full items-center gap-3 rounded-lg px-3 text-[14px] font-medium outline-offset-[-2px] transition-colors hover:bg-ink/[0.05] focus-visible:outline-[3px] focus-visible:outline-yellow motion-reduce:transition-none'

  return (
    <div ref={root} className="relative">
      <button
        ref={trigger}
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`Account menu for ${user.name}`}
        onClick={() => setOpen((o) => !o)}
        className="flex h-11 items-center gap-2.5 rounded-full border border-ink/12 bg-white/70 py-1 pl-1 pr-2.5 outline-offset-2 transition-[border-color,box-shadow] hover:border-ink/30 hover:shadow-[0_6px_18px_-12px_rgb(6_11_7/0.4)] focus-visible:outline-[3px] focus-visible:outline-yellow motion-reduce:transition-none sm:pr-3.5"
      >
        <Avatar user={user} size="size-9" />
        <span className="max-w-[200px] truncate whitespace-nowrap text-[14px] font-semibold text-ink max-sm:hidden md:max-w-none">{user.name}</span>
        <ChevronDown size={15} aria-hidden="true" className={`text-ink/55 transition-transform duration-200 motion-reduce:transition-none ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div
          role="menu"
          aria-label="Account"
          className="absolute right-0 top-[calc(100%+8px)] z-40 w-[272px] rounded-2xl border border-ink/12 bg-cream p-2 shadow-[0_24px_48px_-20px_rgb(6_11_7/0.35)]"
        >
          <div className="flex items-center gap-3 px-3 pb-3 pt-2.5">
            <Avatar user={user} size="size-10 shrink-0" />
            <div className="min-w-0">
              <p className="break-words text-[14.5px] font-semibold leading-snug text-ink">{user.name}</p>
              {user.email && <p className="break-all text-[12.5px] text-ink/55">{user.email}</p>}
            </div>
          </div>
          <div className="border-t border-ink/10 pt-1.5">
            {APP_NAV.map(({ label, href, icon: Icon }) => (
              <a key={label} role="menuitem" href={href} aria-current={label === active ? 'page' : undefined} className={`${item} ${label === active ? 'bg-ink/[0.05] text-ink' : 'text-ink/75'}`}>
                <Icon size={16} aria-hidden="true" className="shrink-0" />
                {label}
              </a>
            ))}
          </div>
          <div className="mt-1.5 border-t border-ink/10 pt-1.5">
            <button type="button" role="menuitem" onClick={() => void signOut()} disabled={busy} className={`${item} text-ink/75 disabled:opacity-60`}>
              <LogOut size={16} aria-hidden="true" className="shrink-0" />
              {busy ? 'Logging out…' : 'Log out'}
            </button>
            {failed && (
              <p role="alert" className="px-3 pb-1 pt-1 text-[12.5px] text-ink/65">
                We couldn’t log you out. Please try again.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default AccountMenu
