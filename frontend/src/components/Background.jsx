import { memo } from 'react'
import Aurora from './reactbits/Aurora'
import Particles from './reactbits/Particles'
import { BackgroundBeams } from './aceternity/background-beams'
import { useIsMobile } from '../lib/hooks'

/**
 * Full-screen, non-interactive animated background.
 *  1. Fluid gradient blobs (CSS)             — slow drifting colour fields
 *  2. Aurora           (React Bits, WebGL2)   — flowing aurora ribbons that follow the cursor
 *  3. Grid + vignette                         — depth
 *  4. Background Beams (Aceternity UI, SVG)   — travelling light beams
 *  5. Particles        (React Bits, WebGL2)   — connected particles that repel from the cursor, burst on click
 */
function Background({ theme = 'dark' }) {
  const light = theme === 'light'
  const mobile = useIsMobile()

  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden bg-bg transition-colors duration-500" aria-hidden="true">
      {/* Deep base gradient */}
      <div
        className="absolute inset-0"
        style={{
          background: light
            ? 'radial-gradient(120% 80% at 50% -10%, #e4e2ff 0%, #f3f4ff 55%, #eef2ff 100%)'
            : 'radial-gradient(120% 80% at 50% -10%, #12124a 0%, #070816 50%, #04050d 100%)',
        }}
      />

      {/* Fluid gradient blobs */}
      <div className={`absolute inset-0 ${light ? 'opacity-40' : 'opacity-70'}`}>
        <div className="animate-blob absolute -top-40 -left-32 h-[46vmax] w-[46vmax] rounded-full bg-violet-glow/40 blur-[110px]" />
        <div className="animate-blob absolute top-1/3 -right-40 h-[42vmax] w-[42vmax] rounded-full bg-electric/35 blur-[120px] [animation-delay:-8s]" />
        <div className="animate-blob absolute -bottom-52 left-1/4 h-[40vmax] w-[40vmax] rounded-full bg-cyan-glow/25 blur-[120px] [animation-delay:-15s]" />
      </div>

      {/* Aurora ribbons (WebGL) */}
      <div className="absolute inset-0">
        <Aurora
          colorStops={light ? ['#7c6cff', '#38bdf8', '#a78bfa'] : ['#7c3aed', '#22d3ee', '#4f7cff']}
          amplitude={1.25}
          blend={0.65}
          speed={0.8}
          height={0.5}
          glow={0.75}
          layers={mobile ? 2 : 3}
          brightness={light ? 0.9 : 1.15}
          opacity={light ? 0.75 : 0.9}
          lightMode={light}
          dpr={1}
        />
      </div>

      {/* Grid with radial mask */}
      <div
        className="grid-bg absolute inset-0 opacity-70"
        style={{
          WebkitMaskImage: 'radial-gradient(ellipse 70% 60% at 50% 30%, #000 20%, transparent 75%)',
          maskImage: 'radial-gradient(ellipse 70% 60% at 50% 30%, #000 20%, transparent 75%)',
        }}
      />

      {/* Light beams */}
      {!light && <BackgroundBeams className="opacity-60" />}

      {/* Interactive particles */}
      <div className="absolute inset-0">
        <Particles
          particleCount={mobile ? 55 : 150}
          particleSpread={10}
          speed={0.12}
          particleColors={light ? ['#6d5dfc', '#0ea5e9', '#7c3aed'] : ['#a78bfa', '#67e8f9', '#93c5fd', '#ffffff']}
          moveParticlesOnHover
          hoverEffect="repel"
          hoverRadius={170}
          particleHoverFactor={1.4}
          particleBaseSize={mobile ? 70 : 90}
          sizeRandomness={1.2}
          connections={!mobile}
          connectionDistance={120}
          clickBurst
          drift="up"
          driftSpeed={0.6}
          glow={0.7}
          twinkle={0.5}
          disableRotation={false}
          lightMode={light}
          opacity={light ? 0.8 : 1}
          alphaParticles={false}
        />
      </div>

      {/* Vignette */}
      <div
        className="absolute inset-0"
        style={{
          background: light
            ? 'radial-gradient(ellipse at center, transparent 55%, rgba(243,244,255,0.85) 100%)'
            : 'radial-gradient(ellipse at center, transparent 50%, rgba(2,3,10,0.75) 100%)',
        }}
      />
    </div>
  )
}

export default memo(Background)

