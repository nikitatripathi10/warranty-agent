import { useState, useEffect, useCallback } from 'react'
import { motion } from 'motion/react'
import { GlassCard, Button, Spinner } from './ui'
import Icon from './Icon'

/**
 * "Add bills from WhatsApp" — links this workspace to the Warranty Agent WhatsApp bot.
 *
 * The user generates a short-lived code here and sends `LINK <code>` to the bot from
 * their phone; sending it from the phone proves they control that number. After that,
 * forwarding a bill photo / PDF (or pasting order details) saves it to this account.
 */
export default function WhatsAppLinkCard({ apiBase, userId, addToast }) {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [code, setCode] = useState(null)
  const [copied, setCopied] = useState(false)

  const loadStatus = useCallback(async () => {
    if (!userId) return
    try {
      const res = await fetch(`${apiBase}/whatsapp/status?user_id=${encodeURIComponent(userId)}`)
      if (!res.ok) throw new Error('status failed')
      setStatus(await res.json())
    } catch {
      setStatus(null)
    } finally {
      setLoading(false)
    }
  }, [apiBase, userId])

  useEffect(() => {
    loadStatus()
  }, [loadStatus])

  // While a code is on screen, poll so the card flips to "linked" as soon as the user sends it.
  useEffect(() => {
    if (!code || status?.linked) return undefined
    const id = setInterval(loadStatus, 4000)
    return () => clearInterval(id)
  }, [code, status?.linked, loadStatus])

  useEffect(() => {
    if (status?.linked && code) {
      setCode(null)
      addToast?.('WhatsApp linked — you can now forward bills to the bot.', 'success')
    }
  }, [status?.linked, code, addToast])

  const generateCode = async () => {
    setBusy(true)
    try {
      const res = await fetch(`${apiBase}/whatsapp/link-code?user_id=${encodeURIComponent(userId)}`, {
        method: 'POST',
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.detail || 'Could not create a link code')
      setCode(data)
      setCopied(false)
    } catch (err) {
      addToast?.(err.message, 'error')
    } finally {
      setBusy(false)
    }
  }

  const unlink = async () => {
    setBusy(true)
    try {
      const res = await fetch(`${apiBase}/whatsapp/link?user_id=${encodeURIComponent(userId)}`, {
        method: 'DELETE',
      })
      if (!res.ok) throw new Error('Could not disconnect WhatsApp')
      setCode(null)
      await loadStatus()
      addToast?.('WhatsApp disconnected.', 'info')
    } catch (err) {
      addToast?.(err.message, 'error')
    } finally {
      setBusy(false)
    }
  }

  const copyCommand = async () => {
    try {
      await navigator.clipboard.writeText(`LINK ${code.code}`)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      addToast?.('Could not copy — type the code manually.', 'error')
    }
  }

  const botNumber = status?.bot_number ? `+${status.bot_number}` : null

  return (
    <GlassCard className="p-5 sm:p-6">
      <div className="flex items-start gap-3">
        <div className="grid size-10 shrink-0 place-items-center rounded-xl bg-emerald-400/15 text-emerald-300 ring-1 ring-line">
          <Icon name="message" size={20} />
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="text-base font-semibold text-fg">Add bills from WhatsApp</h3>
          <p className="mt-0.5 text-xs text-muted">
            Forward a bill photo, a PDF, or paste the order details to the Warranty Agent bot — it reads the bill,
            tracks the warranty and replies within seconds.
          </p>

          <div className="mt-4">
            {loading ? (
              <div className="flex items-center gap-2 text-xs text-subtle">
                <Spinner size={14} />
                <span>Checking WhatsApp…</span>
              </div>
            ) : !status ? (
              <p className="text-xs text-subtle">Couldn&rsquo;t check WhatsApp status right now.</p>
            ) : !status.configured ? (
              <p className="rounded-xl border border-line bg-glass/40 p-3 text-xs text-muted">
                The WhatsApp bot isn&rsquo;t switched on for this server yet. Once the server owner adds Twilio WhatsApp
                Sandbox or Meta Cloud API credentials (see DEPLOYMENT.md), this button will light up.
              </p>
            ) : status.linked ? (
              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-2 text-sm text-fg">
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-400/15 px-2.5 py-1 text-xs font-semibold text-emerald-300 ring-1 ring-emerald-400/30">
                    <Icon name="check" size={12} /> Linked
                  </span>
                  <span className="font-mono text-xs text-muted">{status.phone_masked}</span>
                </div>
                <p className="text-xs text-muted">
                  Send bills to{' '}
                  <span className="font-semibold text-fg">{botNumber || 'the Warranty Agent number'}</span>. Reply{' '}
                  <span className="font-mono text-fg">LIST</span> to see what expires soonest.
                </p>
                {status.sandbox_join_code && (
                  <p className="text-[0.7rem] text-subtle">
                    Using Twilio Sandbox: if the bot stops replying after 72 hours, resend{' '}
                    <span className="font-mono text-fg">{status.sandbox_join_code}</span>.
                  </p>
                )}
                <Button variant="secondary" size="sm" onClick={unlink} disabled={busy}>
                  {busy ? <Spinner size={14} /> : <span>Disconnect WhatsApp</span>}
                </Button>
              </div>
            ) : code ? (
              <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="space-y-3">
                {code.sandbox_join_code && (
                  <div className="rounded-xl border border-emerald-400/30 bg-emerald-400/10 p-3 space-y-2">
                    <div className="text-[0.68rem] font-semibold uppercase tracking-wider text-emerald-300">
                      Step 1 (first time only) · Join sandbox
                    </div>
                    <p className="text-xs text-muted">
                      Send <code className="font-mono font-semibold text-fg">{code.sandbox_join_code}</code> to{' '}
                      <span className="font-semibold text-fg">{botNumber || 'the bot'}</span> on WhatsApp first:
                    </p>
                    {code.sandbox_join_link && (
                      <a
                        href={code.sandbox_join_link}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-500/80 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-emerald-500"
                      >
                        <Icon name="externalLink" size={13} />
                        <span>1. Join Sandbox</span>
                      </a>
                    )}
                  </div>
                )}

                <p className="text-xs text-muted">
                  {code.sandbox_join_code ? 'Step 2: Send ' : 'Send this message to '}
                  {code.sandbox_join_code && (
                    <>
                      this code to <span className="font-semibold text-fg">{botNumber || 'the bot'}</span>{' '}
                    </>
                  )}
                  {!code.sandbox_join_code && (
                    <>
                      <span className="font-semibold text-fg">{botNumber || 'the bot'}</span> on WhatsApp{' '}
                    </>
                  )}
                  within {code.expires_in_minutes} minutes:
                </p>
                <div className="flex flex-wrap items-center gap-2">
                  <code className="rounded-xl border border-line bg-field px-4 py-2 font-mono text-lg font-bold tracking-widest text-cyan-glow">
                    LINK {code.code}
                  </code>
                  <Button variant="secondary" size="sm" onClick={copyCommand}>
                    <Icon name={copied ? 'check' : 'copy'} size={14} />
                    <span>{copied ? 'Copied' : 'Copy'}</span>
                  </Button>
                  {code.deep_link && (
                    <a
                      href={code.deep_link}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-500 px-3.5 py-2 text-xs font-semibold text-white transition hover:bg-emerald-600"
                    >
                      <Icon name="externalLink" size={13} />
                      <span>{code.sandbox_join_code ? '2. Open WhatsApp' : 'Open WhatsApp'}</span>
                    </a>
                  )}
                </div>
                <p className="flex items-center gap-2 text-[0.7rem] text-subtle">
                  <Spinner size={12} />
                  <span>Waiting for your message…</span>
                </p>
              </motion.div>
            ) : (
              <Button variant="primary" size="md" onClick={generateCode} disabled={busy}>
                {busy ? <Spinner size={15} /> : <Icon name="message" size={16} />}
                <span>Link my WhatsApp</span>
              </Button>
            )}
          </div>
        </div>
      </div>
    </GlassCard>
  )
}

