import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import Icon from './Icon'
import { Spinner } from './ui'

const SUGGESTED_QUESTIONS = [
  'Which purchases can I still return?',
  'Which warranties expire soon?',
  'What is the total value of my purchases?',
]

/**
 * Floating assistant. Every answer comes from the backend `/agent/query`
 * endpoint, which answers from the signed-in user's stored purchase records.
 */
export default function FloatingAgentModal({ apiBase, userId }) {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    if (isOpen) messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isOpen])

  if (!userId) return null

  const handleSend = async (textToSend) => {
    const query = (textToSend || input).trim()
    if (!query || loading) return

    setMessages(prev => [...prev, { id: `user-${Date.now()}`, sender: 'user', text: query }])
    setInput('')
    setLoading(true)

    let reply
    try {
      const res = await fetch(`${apiBase}/agent/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, question: query }),
        signal: AbortSignal.timeout(30000),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
      reply = data.answer
    } catch (err) {
      reply = `Sorry, I couldn't get an answer: ${err.message}`
    }

    setMessages(prev => [...prev, { id: `bot-${Date.now()}`, sender: 'bot', text: reply }])
    setLoading(false)
  }

  return (
    <>
      <motion.button
        type="button"
        onClick={() => setIsOpen(true)}
        whileHover={{ scale: 1.04 }}
        whileTap={{ scale: 0.96 }}
        className="fixed bottom-24 right-4 z-50 flex items-center gap-2 rounded-full border border-line-strong bg-surface px-4 py-2.5 text-fg shadow-lg backdrop-blur-xl transition hover:bg-glass-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-violet-glow/60 lg:bottom-6 lg:right-6"
        aria-label="Open warranty assistant"
      >
        <Icon name="bot" size={17} className="text-violet-300" />
        <span className="hidden text-xs font-semibold sm:inline">Ask assistant</span>
      </motion.button>

      <AnimatePresence>
        {isOpen && (
          <div className="fixed inset-0 z-50 flex items-end justify-end p-0 sm:items-center sm:p-6">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsOpen(false)}
              className="absolute inset-0 bg-black/60"
            />

            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 30 }}
              transition={{ type: 'spring', stiffness: 280, damping: 28 }}
              role="dialog"
              aria-label="Warranty assistant"
              className="relative flex h-[85vh] w-full max-w-lg flex-col overflow-hidden rounded-t-3xl border border-line bg-surface shadow-2xl sm:h-[600px] sm:rounded-3xl"
            >
              <div className="flex items-center justify-between border-b border-line px-5 py-4">
                <div className="flex items-center gap-3">
                  <div className="grid size-9 place-items-center rounded-xl bg-violet-glow/15 text-violet-300 ring-1 ring-line">
                    <Icon name="bot" size={18} />
                  </div>
                  <div>
                    <h3 className="font-display text-sm font-semibold text-fg">Warranty assistant</h3>
                    <p className="text-[11px] text-muted">Answers from your saved purchases</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setIsOpen(false)}
                  className="grid size-8 place-items-center rounded-xl text-muted transition hover:bg-white/10 hover:text-fg"
                  aria-label="Close"
                >
                  <Icon name="x" size={16} />
                </button>
              </div>

              <div className="flex-1 space-y-3 overflow-y-auto p-4">
                {messages.length === 0 && (
                  <p className="text-xs leading-relaxed text-muted">
                    Ask about return windows, warranty expiry dates, or anything in your tracked purchases.
                  </p>
                )}
                {messages.map(m => (
                  <div key={m.id} className={`flex ${m.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div
                      className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                        m.sender === 'user'
                          ? 'bg-violet-glow/25 text-fg'
                          : 'border border-line bg-glass text-fg'
                      }`}
                    >
                      {m.text}
                    </div>
                  </div>
                ))}
                {loading && (
                  <div className="flex items-center gap-2 text-xs text-muted">
                    <Spinner size={14} />
                    <span>Looking through your records…</span>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              <div className="overflow-x-auto border-t border-line px-3 py-2">
                <div className="flex gap-1.5 whitespace-nowrap">
                  {SUGGESTED_QUESTIONS.map(q => (
                    <button
                      key={q}
                      type="button"
                      onClick={() => handleSend(q)}
                      className="rounded-full border border-line bg-glass px-2.5 py-1 text-[11px] text-muted transition hover:border-line-strong hover:text-fg"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>

              <form
                onSubmit={e => {
                  e.preventDefault()
                  handleSend()
                }}
                className="flex items-center gap-2 border-t border-line p-3"
              >
                <input
                  type="text"
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  placeholder="Ask about your warranties or returns…"
                  className="flex-1 rounded-xl border border-line bg-field px-3.5 py-2 text-sm text-fg outline-none placeholder:text-subtle focus:border-violet-glow/70"
                />
                <button
                  type="submit"
                  disabled={loading || !input.trim()}
                  aria-label="Send"
                  className="grid size-9 place-items-center rounded-xl bg-violet-glow/30 text-fg transition hover:bg-violet-glow/45 disabled:opacity-40"
                >
                  <Icon name="send" size={15} />
                </button>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </>
  )
}
