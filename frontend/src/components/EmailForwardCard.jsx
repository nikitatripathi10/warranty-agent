import { useState, useEffect, useCallback } from 'react'
import { GlassCard, Button, Spinner } from './ui'
import Icon from './Icon'

/**
 * "Forward bills by email" — shows the user's private forwarding address.
 *
 * Forwarding an order / invoice email from any mail app (Gmail, Outlook, Yahoo, Apple Mail)
 * to bills+<token>@<domain> saves it to the vault. It needs no Gmail permission at all.
 * Gmail also sends a one-time confirmation code to that address before it will auto-forward;
 * the backend captures it and this card shows it so the user can paste it into Gmail.
 */
export default function EmailForwardCard({ apiBase, userId, addToast }) {
  const [info, setInfo] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [copied, setCopied] = useState(false)

  const base = `${apiBase}/ingestion/forwarding-address`

  const load = useCallback(async () => {
    if (!userId) return
    try {
      const res = await fetch(`${base}?user_id=${encodeURIComponent(userId)}`)
      if (!res.ok) throw new Error('load failed')
      setInfo(await res.json())
    } catch {
      setInfo(null)
    } finally {
      setLoading(false)
    }
  }, [base, userId])

  useEffect(() => {
    load()
  }, [load])

  const copyAddress = async () => {
    try {
      await navigator.clipboard.writeText(info.address)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      addToast?.('Could not copy — select the address and copy it manually.', 'error')
    }
  }

  const rotate = async () => {
    if (!window.confirm('Create a new address? The current one will stop working immediately.')) return
    setBusy(true)
    try {
      const res = await fetch(`${base}/rotate?user_id=${encodeURIComponent(userId)}`, { method: 'POST' })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.detail || 'Could not create a new address')
      setInfo(data)
      addToast?.('New forwarding address created.', 'success')
    } catch (err) {
      addToast?.(err.message, 'error')
    } finally {
      setBusy(false)
    }
  }

  return (
    <GlassCard className="p-5 sm:p-6">
      <div className="flex items-start gap-3">
        <div className="grid size-10 shrink-0 place-items-center rounded-xl bg-sky-400/15 text-sky-300 ring-1 ring-line">
          <Icon name="mail" size={20} />
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="text-base font-semibold text-fg">Forward bills by email</h3>
          <p className="mt-0.5 text-xs text-muted">
            Forward any order or invoice email to your private address below — from Gmail, Outlook, Yahoo or any mail
            app. No Gmail permission needed.
          </p>

          <div className="mt-4 space-y-3">
            {loading ? (
              <div className="flex items-center gap-2 text-xs text-subtle">
                <Spinner size={14} />
                <span>Loading your address…</span>
              </div>
            ) : !info ? (
              <p className="text-xs text-subtle">Couldn&rsquo;t load your forwarding address right now.</p>
            ) : !info.enabled ? (
              <p className="rounded-xl border border-line bg-glass/40 p-3 text-xs text-muted">
                Forward-to-email isn&rsquo;t switched on for this server yet. Once the server owner connects a mail
                domain (see DEPLOYMENT.md), your private address will appear here.
              </p>
            ) : (
              <>
                <div className="flex flex-wrap items-center gap-2">
                  <code className="break-all rounded-xl border border-line bg-field px-3 py-2 font-mono text-sm font-semibold text-cyan-glow">
                    {info.address}
                  </code>
                  <Button variant="secondary" size="sm" onClick={copyAddress}>
                    <Icon name={copied ? 'check' : 'copy'} size={14} />
                    <span>{copied ? 'Copied' : 'Copy'}</span>
                  </Button>
                  <Button variant="secondary" size="sm" onClick={rotate} disabled={busy}>
                    {busy ? <Spinner size={14} /> : <Icon name="refresh" size={14} />}
                    <span>New address</span>
                  </Button>
                </div>

                {info.verification_code && (
                  <div className="rounded-xl border border-amber-400/35 bg-amber-400/10 p-3 text-xs text-muted">
                    <div className="mb-1 text-[0.68rem] font-semibold uppercase tracking-wider text-amber-300">
                      Gmail confirmation code
                    </div>
                    Gmail sent a code to confirm forwarding:{' '}
                    <span className="font-mono text-base font-bold tracking-widest text-fg">
                      {info.verification_code}
                    </span>
                    . Enter it in Gmail → Settings → Forwarding and POP/IMAP.
                  </div>
                )}

                <details className="rounded-xl border border-line bg-glass/30 p-3 text-xs text-muted">
                  <summary className="cursor-pointer select-none font-semibold text-fg">
                    Forward automatically from Gmail (set up once)
                  </summary>
                  <ol className="mt-2 list-decimal space-y-1 pl-5 leading-relaxed">
                    <li>Gmail → Settings → Forwarding and POP/IMAP → Add a forwarding address → paste the address above.</li>
                    <li>Gmail emails a confirmation code to it — it appears in the amber box here (tap reload below).</li>
                    <li>
                      Settings → Filters → Create a filter:{' '}
                      <code className="font-mono text-fg">from:(amazon.in OR flipkart.com) subject:(order OR invoice)</code>{' '}
                      → Forward it to your address.
                    </li>
                  </ol>
                  <button
                    type="button"
                    onClick={load}
                    className="mt-2 inline-flex items-center gap-1 text-cyan-glow hover:underline"
                  >
                    <Icon name="refresh" size={12} />
                    <span>Check for Gmail code</span>
                  </button>
                </details>
              </>
            )}
          </div>
        </div>
      </div>
    </GlassCard>
  )
}

