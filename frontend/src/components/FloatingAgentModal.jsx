import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import Icon from './Icon'
import { Spinner } from './ui'
import { ANIMATION_PALETTES } from '../lib/animation-theme'

const SUGGESTED_QUESTIONS = [
  'Which purchases can I still return?',
  'What warranties are expiring soon?',
  'What is my total protected monetary value?',
  'What are the return terms for my Blinkit order?',
  'How do I claim standard Sony warranty in India?',
]

export default function FloatingAgentModal({
  purchases = [],
  alerts = [],
  activePalette = 'cyberpunk',
  onNavigate,
}) {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      sender: 'bot',
      text: "Hello Nikita! I'm your AI Purchase & Warranty Guardian. You currently have 5 active purchases tracked across Amazon, Croma, Flipkart, Blinkit, and Reliance Digital. How can I help you today?",
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef(null)

  const palette = ANIMATION_PALETTES[activePalette] || ANIMATION_PALETTES.cyberpunk

  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, isOpen])

  const handleSend = (textToSend) => {
    const query = (textToSend || input).trim()
    if (!query) return

    const userMsg = { id: `user-${Date.now()}`, sender: 'user', text: query }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    setTimeout(() => {
      let reply = ''
      const lower = query.toLowerCase()

      if (lower.includes('return') || lower.includes('return window')) {
        reply =
          'You currently have 1 critical return window: your Boat Wave Call Smartwatch (purchased on Blinkit) has 3 days remaining before its return period closes on March 4, 2026. All other items have surpassed their return windows and are now covered under manufacturer warranty.'
      } else if (lower.includes('expir') || lower.includes('soon') || lower.includes('alert')) {
        reply =
          'Your highest priority warranty alert is the Sony WH-1000XM5 Wireless Headphones (Amazon India) expiring in 14 days (10 October 2026). I recommend testing the battery and headband hinge now in case you need complimentary Sony authorized service replacement.'
      } else if (lower.includes('value') || lower.includes('total') || lower.includes('worth') || lower.includes('cost')) {
        const total = purchases.reduce((acc, p) => acc + (Number(p.price) || 0), 0)
        reply = `You currently have ₹${total.toLocaleString('en-IN')} in total protected asset value indexed across 5 items. The highest value item is your Apple MacBook Air M3 (₹1,14,900 from Croma), followed by your Dyson V12 Cordless Vacuum (₹44,900).`
      } else if (lower.includes('sony')) {
        reply =
          'Your Sony WH-1000XM5 Noise Cancelling Headphones carry a 1-year official Sony India warranty covering transducer failure, ANC microphones, and battery defects. Visit any Sony Center or call 1800-103-7799 with invoice demo-1.'
      } else if (lower.includes('blinkit')) {
        reply =
          'Quick commerce orders from Blinkit have a strict 3-day replacement/return window for personal electronics. After March 4, you must claim remaining warranty directly through boAt service centers.'
      } else {
        reply = `Based on your indexed portfolio of ${purchases.length} items, your coverage is in great health. You have ${alerts.length} active alerts requiring attention this month. Is there a specific product receipt or warranty clause you'd like me to review?`
      }

      setMessages(prev => [
        ...prev,
        { id: `bot-${Date.now()}`, sender: 'bot', text: reply },
      ])
      setLoading(false)
    }, 650)
  }

  return (
    <>
      {/* Floating Launcher Button */}
      <motion.button
        type="button"
        onClick={() => setIsOpen(true)}
        whileHover={{ scale: 1.08 }}
        whileTap={{ scale: 0.92 }}
        className="fixed bottom-6 right-6 z-50 flex items-center gap-2.5 rounded-full px-4 py-3 text-white shadow-2xl backdrop-blur-xl transition focus:outline-none"
        style={{
          background: `linear-gradient(135deg, ${palette.primary} 0%, #7928ca 50%, ${palette.secondary} 100%)`,
          boxShadow: `0 8px 32px ${palette.primary}66`,
        }}
        aria-label="Open AI Warranty Assistant"
      >
        <span className="relative flex size-2.5">
          <span className="animate-ping-slow absolute inline-flex size-full rounded-full bg-white opacity-85" />
          <span className="relative inline-flex size-2.5 rounded-full bg-white" />
        </span>
        <Icon name="bot" size={19} className="text-white" />
        <span className="hidden sm:inline text-xs font-bold tracking-wide uppercase">AI Assistant</span>
      </motion.button>

      {/* Slide-over Drawer / Modal */}
      <AnimatePresence>
        {isOpen && (
          <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-end p-0 sm:p-6">
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsOpen(false)}
              className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            />

            {/* Modal Dialog */}
            <motion.div
              initial={{ opacity: 0, y: 40, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 40, scale: 0.95 }}
              transition={{ type: 'spring', stiffness: 280, damping: 26 }}
              className="relative flex h-[85vh] sm:h-[620px] w-full max-w-lg flex-col rounded-t-3xl sm:rounded-3xl border border-white/15 bg-slate-950/90 shadow-2xl backdrop-blur-2xl overflow-hidden"
            >
              {/* Header */}
              <div
                className="flex items-center justify-between border-b border-white/10 px-5 py-4"
                style={{
                  background: `linear-gradient(to right, ${palette.primary}18, ${palette.secondary}18)`,
                }}
              >
                <div className="flex items-center gap-3">
                  <div
                    className="grid size-9 place-items-center rounded-xl text-white shadow-md"
                    style={{
                      background: `linear-gradient(135deg, ${palette.primary}, ${palette.secondary})`,
                    }}
                  >
                    <Icon name="bot" size={19} />
                  </div>
                  <div>
                    <h3 className="font-display text-sm font-bold text-fg">AI Warranty Copilot</h3>
                    <p className="text-[11px] text-muted">Real-time assistant for Nikita's purchases</p>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => setIsOpen(false)}
                  className="grid size-8 place-items-center rounded-xl text-muted hover:text-fg hover:bg-white/10 transition"
                  aria-label="Close"
                >
                  <Icon name="x" size={16} />
                </button>
              </div>

              {/* Chat Message List */}
              <div className="flex-1 overflow-y-auto p-4 space-y-3.5">
                {messages.map((m) => (
                  <div
                    key={m.id}
                    className={`flex gap-2.5 ${m.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    {m.sender === 'bot' && (
                      <div
                        className="grid size-7 shrink-0 place-items-center rounded-lg text-white"
                        style={{
                          background: `linear-gradient(135deg, ${palette.primary}, ${palette.secondary})`,
                        }}
                      >
                        <Icon name="bot" size={13} />
                      </div>
                    )}

                    <div
                      className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-xs sm:text-sm leading-relaxed ${
                        m.sender === 'user'
                          ? 'bg-linear-to-r from-violet-600 to-indigo-600 text-white shadow-md'
                          : 'glass border border-white/10 bg-white/5 text-fg'
                      }`}
                    >
                      {m.text}
                    </div>
                  </div>
                ))}

                {loading && (
                  <div className="flex items-center gap-2 text-xs text-muted">
                    <Spinner size={14} />
                    <span>Analyzing warranty clauses &amp; receipt timestamps…</span>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Suggested Questions */}
              <div className="border-t border-white/10 bg-black/40 px-3 py-2 overflow-x-auto">
                <div className="flex gap-1.5 whitespace-nowrap">
                  {SUGGESTED_QUESTIONS.map((q, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => handleSend(q)}
                      className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[11px] text-muted hover:border-white/20 hover:text-fg transition"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>

              {/* Input Area */}
              <div className="border-t border-white/10 p-3 bg-slate-950/80">
                <form
                  onSubmit={(e) => {
                    e.preventDefault()
                    handleSend()
                  }}
                  className="flex items-center gap-2"
                >
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Ask anything about your warranties, returns, or claims…"
                    className="flex-1 rounded-xl border border-white/15 bg-white/5 px-3.5 py-2 text-xs text-fg placeholder:text-muted focus:border-violet-400 focus:outline-none"
                  />
                  <button
                    type="submit"
                    disabled={loading || !input.trim()}
                    className="grid size-9 place-items-center rounded-xl text-white transition disabled:opacity-40"
                    style={{
                      background: `linear-gradient(135deg, ${palette.primary}, ${palette.secondary})`,
                    }}
                  >
                    <Icon name="send" size={15} />
                  </button>
                </form>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </>
  )
}
