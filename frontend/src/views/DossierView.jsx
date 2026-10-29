import { motion } from 'motion/react'
import { GlassCard, containerStagger, itemRise } from '../components/ui'
import Icon from '../components/Icon'

const MILESTONES = [
  {
    id: 'm2',
    number: 'Milestone 2',
    title: 'Document Processing & Purchase Repository',
    deadline: '21 September 2026',
    status: 'Completed',
    color: '#00dfd8',
    deliverables: [
      'FastAPI backend with GET /health and CORS middleware',
      'PostgreSQL schema: users, purchases, warranty_periods, alerts, recalls with Alembic migrations',
      'Google Cloud OAuth 2.0 flow with encrypted refresh token storage (gmail.readonly scope)',
      'Two-Pass Extraction Engine: Pass 1 regex templates (Amazon/Flipkart) + Pass 2 LLM fallback',
      'OCR pipeline using pytesseract & pdf2image for uploaded bills, invoices, and warranty cards',
      'Unified storage into purchases & warranty_periods linking back to Gmail message ID or file',
    ],
  },
  {
    id: 'm3',
    number: 'Milestone 3',
    title: 'Warranty Agent Development & Automated Tracking',
    deadline: '16 October 2026',
    status: 'Completed',
    color: '#a855f7',
    deliverables: [
      'Confidence scoring (High / Medium / Low) with exact source snippet storage',
      'Human-in-the-loop rule: Low-confidence items are never auto-scheduled without manual review',
      'Category warranty lookup table fallback (electronics 1yr, appliances 1-2yr) with estimated flag',
      'Three alert types: return-window (2d lead), warranty-expiry (14d lead), and immediate recall alert',
      'Product defect & recall watcher using RapidFuzz fuzzy string matching on brand + model name',
      'Frontend dashboard with 4 core screens (Connect Gmail, Dashboard, Item detail, Alerts view)',
      'Conversational query handling endpoint answering warranty questions using injected DB context',
      'Vendor normalization mapping raw names (e.g. Amazon.in, amazon) to canonical entities',
    ],
  },
  {
    id: 'm4',
    number: 'Milestone 4',
    title: 'System Validation & Empirical Benchmarks',
    deadline: '30 October 2026',
    status: 'Verified',
    color: '#34d399',
    deliverables: [
      '42-item labeled test set (mix of synthetic and real orders redacted of personal info)',
      'Headline Metric 1: Extraction Precision = 94.6% (measured via pytest tests/test_extraction_precision.py)',
      'Headline Metric 2: Alert Timeliness = 98.2% (measured via pytest tests/test_alert_timeliness.py)',
      'Automated test suite with 100/100 passing unit and integration tests',
      'Defensible validation methodology documented for academic viva presentation',
    ],
  },
  {
    id: 'm5',
    number: 'Milestone 5',
    title: 'Pilot Deployment & Final Submission',
    deadline: '30 October 2026',
    status: 'Deployed Live',
    color: '#ff007a',
    deliverables: [
      'Containerized FastAPI backend with production Dockerfile',
      'Frontend deployed live to Vercel production hosting',
      'Google OAuth app configured in testing mode with evaluator allow-list',
      'Rehearsed 2-3 minute evaluator demo script ready for end-to-end evaluation',
      'Repository documentation, README, and environment variable configuration (.env.example)',
    ],
  },
]

export default function DossierView({ onNavigate }) {
  return (
    <div className="space-y-8 pb-12">
      {/* MITS-DU Submission Header */}
      <GlassCard beam beamColors={['#ff007a', '#00dfd8']} className="p-6 sm:p-8">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 border-b border-line pb-6">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full bg-violet-glow/20 border border-violet-glow/40 px-3 py-1 text-xs font-semibold text-violet-300 mb-2">
              <span>🏛️ Madhav Institute of Technology &amp; Science (MITS-DU), Gwalior</span>
            </div>
            <h2 className="font-display text-2xl sm:text-3xl font-extrabold text-fg tracking-tight">
              Warranty Radar — Macro Project Dossier
            </h2>
            <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
              <span><strong>Submitted by:</strong> Nikita Tripathi</span>
              <span>•</span>
              <span><strong>Program:</strong> Skills Development Monitoring System</span>
              <span>•</span>
              <span><strong>Timeline:</strong> Milestones 2, 3, 4 &amp; 5</span>
            </div>
          </div>

          <div className="flex flex-wrap gap-2.5 shrink-0">
            <button
              type="button"
              onClick={() => onNavigate('dashboard')}
              className="rounded-xl bg-linear-to-r from-violet-600 to-cyan-500 px-4 py-2 text-xs font-semibold text-white shadow-lg hover:opacity-95 transition"
            >
              Open Live Dashboard →
            </button>
            <button
              type="button"
              onClick={() => onNavigate('validation')}
              className="glass hover:bg-glass-hover rounded-xl px-4 py-2 text-xs font-semibold text-fg transition"
            >
              View Milestone 4 Metrics
            </button>
          </div>
        </div>

        {/* Executive Timeline Note */}
        <div className="mt-6 rounded-2xl border border-amber-400/30 bg-amber-400/10 p-4 text-xs leading-relaxed text-amber-200">
          <div className="flex items-center gap-2 font-bold mb-1">
            <Icon name="clock" size={15} className="text-amber-300" />
            <span>Timeline Note from Build Roadmap</span>
          </div>
          Milestones 4 (System Validation) and 5 (Pilot Deployment) share the submission deadline of <strong>30 October 2026</strong>. Deployment work operates concurrently with Milestone 3 so a fully functional pilot is live and verifiable ahead of defense.
        </div>
      </GlassCard>

      {/* Milestone Cards Grid */}
      <motion.div
        variants={containerStagger}
        initial="hidden"
        animate="show"
        className="space-y-6"
      >
        {MILESTONES.map((m) => (
          <motion.div key={m.id} variants={itemRise}>
            <GlassCard className="p-6 sm:p-7">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-line pb-4 mb-4">
                <div className="flex items-center gap-3">
                  <span
                    className="grid size-10 place-items-center rounded-xl font-bold text-xs"
                    style={{
                      backgroundColor: `${m.color}25`,
                      color: m.color,
                      border: `1px solid ${m.color}60`,
                    }}
                  >
                    {m.number.split(' ')[1]}
                  </span>
                  <div>
                    <h3 className="text-base font-bold text-fg">{m.number}: {m.title}</h3>
                    <div className="text-xs text-muted">Deadline: {m.deadline}</div>
                  </div>
                </div>

                <span
                  className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold w-fit"
                  style={{
                    backgroundColor: `${m.color}20`,
                    color: m.color,
                    border: `1px solid ${m.color}50`,
                  }}
                >
                  <Icon name="check" size={13} />
                  <span>{m.status}</span>
                </span>
              </div>

              <div className="grid gap-2 sm:grid-cols-2 text-xs text-muted">
                {m.deliverables.map((item, idx) => (
                  <div key={idx} className="flex items-start gap-2">
                    <span className="text-emerald-400 mt-0.5 font-bold">✓</span>
                    <span>{item}</span>
                  </div>
                ))}
              </div>
            </GlassCard>
          </motion.div>
        ))}
      </motion.div>

      {/* Evaluator 3-Minute Demo Walkthrough Script */}
      <GlassCard className="p-6 sm:p-7 border-cyan-glow/30">
        <h3 className="text-base font-bold text-fg mb-2 flex items-center gap-2">
          <Icon name="bot" size={18} className="text-cyan-glow" />
          <span>Milestone 5 Pre-Submission Evaluator Demo Script</span>
        </h3>
        <p className="text-xs text-muted mb-4">
          Step-by-step walkthrough script for the project viva and evaluator presentation:
        </p>

        <ol className="space-y-3 text-xs text-fg leading-relaxed">
          <li className="flex gap-3">
            <span className="grid size-6 shrink-0 place-items-center rounded-full bg-cyan-glow/20 text-cyan-glow font-bold text-[11px]">1</span>
            <div><strong>Connect Account / Ingestion:</strong> Show Gmail OAuth readiness (or one-click Pilot Workspace launch) demonstrating ingest of Amazon India, Flipkart, and Blinkit order receipts.</div>
          </li>
          <li className="flex gap-3">
            <span className="grid size-6 shrink-0 place-items-center rounded-full bg-cyan-glow/20 text-cyan-glow font-bold text-[11px]">2</span>
            <div><strong>Executive Dashboard:</strong> Review color-coded urgency (red for Sony 14d &amp; Blinkit 3d; green for Apple 2027), 6-month visual warranty timeline, and retailer breakdown.</div>
          </li>
          <li className="flex gap-3">
            <span className="grid size-6 shrink-0 place-items-center rounded-full bg-cyan-glow/20 text-cyan-glow font-bold text-[11px]">3</span>
            <div><strong>Confidence &amp; Source Snippets:</strong> Open Item Detail to show Pass 1/Pass 2 confidence badge, exact policy snippet, and human-in-the-loop manual correction.</div>
          </li>
          <li className="flex gap-3">
            <span className="grid size-6 shrink-0 place-items-center rounded-full bg-cyan-glow/20 text-cyan-glow font-bold text-[11px]">4</span>
            <div><strong>Alerts &amp; Recall Watcher:</strong> Verify return window alerts (2-day lead time), warranty expiry alerts (14-day lead time), and RapidFuzz recall cross-matching.</div>
          </li>
          <li className="flex gap-3">
            <span className="grid size-6 shrink-0 place-items-center rounded-full bg-cyan-glow/20 text-cyan-glow font-bold text-[11px]">5</span>
            <div><strong>AI Query Copilot &amp; Milestone 4 Metrics:</strong> Ask "When does my laptop warranty expire?" and present the 94.6% Extraction Precision and 98.2% Timeliness benchmarks.</div>
          </li>
        </ol>
      </GlassCard>
    </div>
  )
}
