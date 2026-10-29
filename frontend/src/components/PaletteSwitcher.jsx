import { motion } from 'motion/react'
import { ANIMATION_PALETTES } from '../lib/animation-theme'
import Icon from './Icon'

export default function PaletteSwitcher({ activePalette, onSelectPalette }) {
  const current = ANIMATION_PALETTES[activePalette] || ANIMATION_PALETTES.cyberpunk
  const keys = Object.keys(ANIMATION_PALETTES)

  const handleNext = () => {
    const idx = keys.indexOf(activePalette)
    const nextIdx = (idx + 1) % keys.length
    onSelectPalette(keys[nextIdx])
  }

  return (
    <motion.button
      type="button"
      onClick={handleNext}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.94 }}
      title={`Current FX theme: ${current.name} (Click to change)`}
      className="glass hover:border-line-strong group flex items-center gap-2 rounded-xl px-2.5 py-1.5 text-xs font-medium text-fg shadow-sm transition"
    >
      <span className="text-sm">{current.icon}</span>
      <span className="hidden sm:inline text-xs font-semibold">{current.name}</span>
      {/* Mini color dot preview */}
      <span className="flex items-center -space-x-1">
        <span
          className="size-2.5 rounded-full border border-bg shadow-[0_0_6px_currentColor]"
          style={{ backgroundColor: current.primary, color: current.primary }}
        />
        <span
          className="size-2.5 rounded-full border border-bg shadow-[0_0_6px_currentColor]"
          style={{ backgroundColor: current.secondary, color: current.secondary }}
        />
      </span>
      <Icon name="refresh" size={13} className="text-subtle transition-transform group-hover:rotate-180" />
    </motion.button>
  )
}
