import { motion } from 'motion/react'
import Icon from './Icon'

/**
 * High-tech animated Radar HUD scanner visualizer.
 * Fits the "Warranty Radar" theme with rotating scanline sector,
 * pulsing blip targets, concentric range rings, and real-time scanning readout.
 */
export default function RadarScanner({
  size = 280,
  accentColor = '#ff007a',
  secondaryColor = '#00dfd8',
  className = '',
}) {
  const blips = [
    { id: 'b1', x: '68%', y: '28%', label: 'Amazon India · 14d return', pingDelay: 0, color: '#00dfd8' },
    { id: 'b2', x: '32%', y: '62%', label: 'Apple Croma · 1yr warranty', pingDelay: 1.4, color: '#ff007a' },
    { id: 'b3', x: '72%', y: '74%', label: 'Dyson Flipkart · Active', pingDelay: 2.8, color: '#34d399' },
    { id: 'b4', x: '24%', y: '34%', label: 'Blinkit · 3d critical', pingDelay: 0.8, color: '#fbbf24' },
  ]

  return (
    <div
      className={`relative select-none ${className}`}
      style={{ width: size, height: size }}
      aria-hidden="true"
    >
      {/* Outer Glow Halo */}
      <div
        className="absolute inset-0 rounded-full blur-2xl opacity-35"
        style={{
          background: `radial-gradient(circle, ${accentColor} 0%, ${secondaryColor} 60%, transparent 80%)`,
        }}
      />

      {/* Main Radar Screen Container */}
      <div className="relative h-full w-full rounded-full border border-white/15 bg-black/60 shadow-[0_0_40px_rgba(0,0,0,0.8)] backdrop-blur-xl overflow-hidden">
        {/* Concentric Target Rings */}
        <div className="absolute inset-3 rounded-full border border-white/10" />
        <div className="absolute inset-8 rounded-full border border-white/10" />
        <div className="absolute inset-16 rounded-full border border-white/10" />
        <div className="absolute inset-24 rounded-full border border-dashed border-white/15" />

        {/* Crosshair Graticule Lines */}
        <div className="absolute inset-x-0 top-1/2 h-[1px] -translate-y-1/2 bg-white/15" />
        <div className="absolute inset-y-0 left-1/2 w-[1px] -translate-x-1/2 bg-white/15" />

        {/* 45-degree Diagonal Graticule Lines */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="h-[1px] w-full rotate-45 bg-white/8" />
          <div className="h-[1px] w-full -rotate-45 bg-white/8" />
        </div>

        {/* 360-Degree Rotating Sweeper Beam */}
        <motion.div
          animate={{ rotate: 360 }}
          transition={{
            repeat: Infinity,
            duration: 4.5,
            ease: 'linear',
          }}
          className="absolute inset-0 origin-center"
        >
          <div
            className="absolute inset-0"
            style={{
              background: `conic-gradient(from 0deg at 50% 50%, transparent 0deg, transparent 290deg, ${accentColor}33 330deg, ${secondaryColor}99 360deg)`,
            }}
          />
          {/* Leading Laser Sweep Line */}
          <div
            className="absolute top-0 right-1/2 h-1/2 w-[2px] origin-bottom shadow-[0_0_12px_#fff]"
            style={{
              background: `linear-gradient(to top, #ffffff 0%, ${secondaryColor} 100%)`,
            }}
          />
        </motion.div>

        {/* Radar Blips (Pulsing Purchases Detected) */}
        {blips.map((blip) => (
          <div
            key={blip.id}
            className="group absolute -translate-x-1/2 -translate-y-1/2"
            style={{ left: blip.x, top: blip.y }}
          >
            {/* Blip Ping Wave */}
            <motion.span
              animate={{
                scale: [1, 2.8],
                opacity: [0.8, 0],
              }}
              transition={{
                repeat: Infinity,
                duration: 2.2,
                delay: blip.pingDelay,
                ease: 'easeOut',
              }}
              className="absolute -inset-1.5 rounded-full"
              style={{ backgroundColor: blip.color }}
            />
            {/* Blip Core Dot */}
            <span
              className="relative block size-2.5 rounded-full border border-white/80 shadow-[0_0_10px_currentColor]"
              style={{ backgroundColor: blip.color, color: blip.color }}
            />
          </div>
        ))}

        {/* Center Origin Node */}
        <div className="absolute left-1/2 top-1/2 grid size-7 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full border border-white/40 bg-black/90 shadow-[0_0_16px_rgba(255,255,255,0.4)]">
          <Icon name="shieldCheck" size={13} className="text-white" />
        </div>

        {/* HUD Scanner readout overlay */}
        <div className="pointer-events-none absolute bottom-2 inset-x-0 text-center font-mono text-[9px] tracking-wider text-white/50 uppercase">
          SCANNING RANGE · 365 DAYS
        </div>
      </div>
    </div>
  )
}
