import { useEffect, useState } from 'react'
import { AnimatePresence } from 'motion/react'
import { useStore, type DarkPage, type Theme } from './store'
import { useAuth } from './auth'
import { Pop, Scrim } from './Sheet'
import { DebugRecordButton } from './DebugRecorder' // DEBUG: remove before release
import { ApiError, getMe, ownBudgetSpent, setModelTier, sharedBudgetSpent, type Me, type ModelTier } from '../lib/api'

const themes: { id: Theme; label: string }[] = [
  { id: 'system', label: 'Auto' },
  { id: 'light', label: 'Light' },
  { id: 'dark', label: 'Dark' },
]
const usd = (n: number) => `$${n.toFixed(2)}`

/** The account as `GET /me` gives it, read each time the menu opens so the credit is fresh after a job. */
function useMe(open: boolean, token: string | undefined) {
  const [me, setMe] = useState<Me | null | 'failed'>(null)
  useEffect(() => {
    if (!open || !token) return
    let live = true
    setMe(null)
    getMe(token).then(m => { if (live) setMe(m) }, () => { if (live) setMe('failed') })
    return () => { live = false }
  }, [open, token])
  return [me, setMe] as const
}

/** What is left of the account's own budget for model calls. The shared project cap is never shown; when it stops
 *  calls, the API's own sentence says so. */
function Credit({ me }: { me: Me | null | 'failed' }) {
  const b = me && me !== 'failed' ? me.budget : null
  const left = b ? Math.max(0, b.budget_usd - b.spent_usd) : 0
  const used = b && b.budget_usd > 0 ? Math.min(1, b.spent_usd / b.budget_usd) : b ? 1 : 0
  const own = b ? b.spent_usd >= b.budget_usd : false
  return (
    <div className="acct-sec" aria-busy={me === null}>
      <span className="r3-label" id="acct-credit">Credit</span>
      {me === 'failed' ? (
        <span className="acct-credit-note">The credit could not be checked just now.</span>
      ) : (
        <>
          <span className="acct-credit-left">{b ? <><span className="num">{usd(left)}</span> of <span className="num">{usd(b.budget_usd)}</span> left</> : 'Checking…'}</span>
          <span className="meter acct-meter" role="meter" aria-labelledby="acct-credit" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(used * 100)}
            aria-valuetext={b ? `${usd(left)} of ${usd(b.budget_usd)} left` : 'Checking'}>
            <span style={{ width: `${used * 100}%` }} />
          </span>
          {b && !b.can_call_models && <span className="acct-credit-note">{own ? ownBudgetSpent : sharedBudgetSpent}.</span>}
        </>
      )}
    </div>
  )
}

const tiers: { id: ModelTier; label: string; sub: string }[] = [
  { id: 'standard', label: 'Standard', sub: 'Your scores and recordings are not used to train Meta models' },
  { id: 'contributor', label: 'Contributor', sub: 'Cheaper. Meta may use the content to train future models' },
]

/** Which of Meta's two tiers reads this account's books and voice notes (`profiles.model_tier`, `PATCH /me`). The
 *  choice shows at once and is put back, with the reason, when the server refuses it. Standard until the account
 *  has been read, and wherever the server does not know the setting yet. */
function Tier({ me, setMe, token }: { me: Me | null | 'failed'; setMe: (m: Me) => void; token: string | undefined }) {
  const [saving, setSaving] = useState<ModelTier | null>(null)
  const [note, setNote] = useState<string | null>(null)
  const acct = me && me !== 'failed' ? me : null
  const current: ModelTier = saving ?? (acct?.model_tier === 'contributor' ? 'contributor' : 'standard')

  useEffect(() => { if (me === null) setNote(null) }, [me])

  const choose = (t: ModelTier) => {
    if (!acct || !token || saving || t === current) return
    setSaving(t)
    setNote(null)
    setModelTier(t, token).then(m => setMe(m), (e: unknown) => {
      const missing = e instanceof ApiError && (e.status === 404 || e.status === 405)
      setNote(missing ? 'Choosing a model tier is not available on this server yet.'
        : e instanceof ApiError ? e.message : 'The model tier could not be changed just now.')
    }).finally(() => setSaving(null))
  }

  return (
    <div className="acct-sec" aria-busy={me === null || saving !== null}>
      <span className="r3-label" id="acct-tier">Model tier</span>
      <div className={`acct-pages${acct ? '' : ' is-waiting'}`} role="radiogroup" aria-labelledby="acct-tier">
        {tiers.map(t => (
          <button key={t.id} type="button" role="radio" aria-checked={current === t.id} disabled={!acct || !token || saving !== null}
            className="acct-page acct-tier" onClick={() => choose(t.id)}>
            <span className="acct-page-text"><b>{t.label}</b><span>{t.sub}</span></span>
          </button>
        ))}
      </div>
      {me === 'failed' && <span className="acct-credit-note">The model tier could not be checked just now.</span>}
      {note && <span className="acct-credit-note" role="status">{note}</span>}
    </div>
  )
}

const pages: { id: DarkPage; label: string; sub: string }[] = [
  { id: 'dim', label: 'Dimmed paper', sub: 'The page stays paper, turned down for the room' },
  { id: 'invert', label: 'Inverted', sub: 'Light notes on a dark page' },
]

/** The account circle (R3): the account's initial; opens appearance (theme, and how a page reads on the stand in the
 *  dark) and the account itself. A popover growing out of the circle; a clear scrim takes the closing tap; Escape too. */
export function AccountButton({ className = '' }: { className?: string }) {
  const { display, setDisplay, world } = useStore()
  const { session, signOut } = useAuth()
  const [open, setOpen] = useState(false)
  const name = world.account.name || session?.user.email || '?'
  const token = session?.access_token
  const [me, setMe] = useMe(open, token)

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])

  return (
    <div className={`acct ${className}`}>
      <button type="button" className="acct-circle" aria-label="Account and appearance" aria-expanded={open} aria-haspopup="dialog" onClick={() => setOpen(v => !v)}>
        {name.trim()[0]?.toUpperCase()}
      </button>
      <AnimatePresence>{open && <Scrim key="scrim" clear fixed onClose={() => setOpen(false)} />}</AnimatePresence>
      <Pop open={open} origin="top right" className="r3-pop acct-pop" role="dialog" aria-label="Account and appearance">
        <p className="acct-who">
          <span className="acct-name">{name}</span>
          {session?.user.email && session.user.email !== name && <span className="acct-mail">{session.user.email}</span>}
        </p>
        <div className="acct-sec">
          <span className="r3-label" id="acct-theme">Appearance</span>
          <div className="r3-seg is-fill" role="radiogroup" aria-labelledby="acct-theme">
            {themes.map(t => (
              <button key={t.id} type="button" role="radio" aria-checked={display.theme === t.id} onClick={() => setDisplay(d => ({ ...d, theme: t.id }))}>{t.label}</button>
            ))}
          </div>
        </div>
        <div className="acct-sec">
          <span className="r3-label" id="acct-page">Pages on the stand in the dark</span>
          <div className="acct-pages" role="radiogroup" aria-labelledby="acct-page">
            {pages.map(p => (
              <button key={p.id} type="button" role="radio" aria-checked={display.page === p.id} className="acct-page" onClick={() => setDisplay(d => ({ ...d, page: p.id }))}>
                <span className={`acct-swatch is-${p.id}`} aria-hidden="true"><span /><span /><span /></span>
                <span className="acct-page-text"><b>{p.label}</b><span>{p.sub}</span></span>
              </button>
            ))}
          </div>
        </div>
        <Tier me={me} setMe={setMe} token={token} />
        <Credit me={me} />
        <DebugRecordButton />{/* DEBUG: remove before release */}
        <button type="button" className="r3-btn is-quiet acct-out" onClick={() => signOut()}>Sign out</button>
      </Pop>
    </div>
  )
}
