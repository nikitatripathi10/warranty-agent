import { motion } from 'motion/react'
import { GlassCard, Button, Spinner, Textarea } from '../components/ui'
import ResultGrid from '../components/ResultGrid'
import Icon from '../components/Icon'

export default function LookupView({
  testText,
  setTestText,
  testLoading,
  testResult,
  testError,
  onTestExtraction,
  isConnected,
  agentQuestion,
  setAgentQuestion,
  agentAnswer,
  agentLoading,
  onAgentQuery,
}) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-2xl font-bold tracking-tight text-fg sm:text-3xl">
          Quick Lookup &amp; Text Extraction
        </h2>
        <p className="mt-1 text-xs text-muted">
          Test receipt extraction on arbitrary text or consult the AI Warranty Agent about your history.
        </p>
      </div>

      {/* Raw Text Extraction Card */}
      <GlassCard beam beamColors={['#22d3ee', '#8b5cf6']} className="p-6 sm:p-8">
        <div className="mb-4 flex items-center gap-3">
          <div className="grid size-10 place-items-center rounded-xl bg-cyan-glow/20 text-cyan-glow ring-1 ring-line">
            <Icon name="search" size={20} />
          </div>
          <div>
            <h3 className="text-base font-semibold text-fg">Extract from Raw Order Confirmation</h3>
            <p className="text-xs text-muted">
              Paste order confirmation emails, WhatsApp invoices, or SMS receipts to preview extraction without saving.
            </p>
          </div>
        </div>

        <Textarea
          id="extraction-test-input"
          rows={6}
          value={testText}
          onChange={e => setTestText(e.target.value)}
          placeholder={`Paste your order confirmation here, e.g.:\n\nDear Customer,\nThank you for your order from Amazon.in\nOrder #405-9812345 placed on 15 August 2025.\n1 x Sony WH-1000XM5 Headphones · ₹28,990 · 1-year warranty.`}
          className="mb-4 font-mono text-xs"
        />

        <div className="flex justify-end">
          <Button
            id="btn-test-extraction"
            variant="primary"
            size="md"
            onClick={onTestExtraction}
            disabled={!testText.trim() || testLoading}
          >
            {testLoading ? (
              <>
                <Spinner size={15} />
                <span>Analysing Text…</span>
              </>
            ) : (
              <>
                <Icon name="sparkles" size={16} />
                <span>Extract Warranty Details</span>
              </>
            )}
          </Button>
        </div>

        {testError && (
          <div className="mt-4 rounded-xl border border-rose-400/30 bg-rose-400/10 p-3 text-xs text-rose-200">
            {testError}
          </div>
        )}

        {testResult && (
          <div className="mt-6 border-t border-line pt-6">
            <div className="mb-3 text-xs font-semibold uppercase tracking-wider text-cyan-glow">
              Preview Result
            </div>
            <ResultGrid result={testResult} />
          </div>
        )}
      </GlassCard>

      {/* General Warranty Agent Query */}
      {isConnected && (
        <GlassCard className="p-6 sm:p-8">
          <div className="mb-4 flex items-center gap-3">
            <div className="grid size-10 place-items-center rounded-xl bg-violet-glow/20 text-violet-300 ring-1 ring-line">
              <Icon name="bot" size={20} />
            </div>
            <div>
              <h3 className="text-base font-semibold text-fg">Ask the Warranty Agent</h3>
              <p className="text-xs text-muted">Ask anything across your entire tracked purchase history.</p>
            </div>
          </div>

          <div className="flex gap-2">
            <input
              id="agent-question-lookup"
              type="text"
              value={agentQuestion}
              onChange={e => setAgentQuestion(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && onAgentQuery()}
              placeholder="e.g. Which products have warranties expiring this quarter?"
              className="flex-1 rounded-xl border border-line bg-field px-4 py-2.5 text-sm text-fg placeholder:text-subtle outline-none backdrop-blur-md transition hover:border-line-strong focus:border-violet-glow/70 focus:ring-4 focus:ring-violet-glow/15"
            />
            <Button
              variant="primary"
              size="md"
              onClick={onAgentQuery}
              disabled={agentLoading || !agentQuestion.trim()}
            >
              {agentLoading ? <Spinner size={15} /> : <Icon name="send" size={16} />}
            </Button>
          </div>

          {agentAnswer && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-4 flex items-start gap-3 rounded-xl border border-violet-glow/30 bg-violet-glow/10 p-4 text-sm text-fg"
            >
              <span className="text-lg">🤖</span>
              <div className="leading-relaxed">{agentAnswer}</div>
            </motion.div>
          )}
        </GlassCard>
      )}
    </div>
  )
}

