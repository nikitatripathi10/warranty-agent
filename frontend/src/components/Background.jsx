import { memo } from 'react'
import Aurora from './reactbits/Aurora'
import Particles from './reactbits/Particles'
import { BackgroundBeams } from './aceternity/background-beams'
import CursorTorch from './CursorTorch'
import { ANIMATION_PALETTES } from '../lib/animation-theme'
import { useIsMobile } from '../lib/hooks'

/**
 * Deep-space animated background with rich dark contrast so white text and
 * dark glass cards remain crisp while the surrounding canvas feels alive.
 */
function Background({ theme = 'dark', paletteId = 'cyberpunk' }) {
  const light = theme === 'light'
  const mobile = useIsMobile()
  const palette = ANIMATION_PALETTES[paletteId] || ANIMATION_PALETTES.cyberpunk

  return (
    <div
      className="pointer-events-none fixed inset-0 -z-10 overflow-hidden bg-bg transition-colors duration-700"
      aria-hidden="true"
    >
      {/* Deep midnight foundation with side radial glow */}
      <div
        className="absolute inset-0"
        style={{
          background: light
            ? 'radial-gradient(120% 80% at 50% -10%, #eef2ff 0%, #f4f6ff 55%, #e8edff 100%)'
            : 'radial-gradient(90% 60% at 50% -10%, #131b42 0%, #070a18 55%, #04060e 100%)',
        }}
      />

      {/* Ambient drifting orbs on the edges (like the original radial blue/indigo glow) */}
      <div className={`absolute inset-0 ${light ? 'opacity-30' : 'opacity-65'} transition-opacity duration-700`}>
        <div
          className="animate-blob absolute -top-32 -left-32 h-[46vmax] w-[46vmax] rounded-full blur-[120px] transition-colors duration-1000"
          style={{ backgroundColor: palette.blob1 }}
        />
        <div
          className="animate-blob absolute top-1/3 -right-32 h-[44vmax] w-[44vmax] rounded-full blur-[125px] [animation-delay:-8s] transition-colors duration-1000"
          style={{ backgroundColor: palette.blob2 }}
        />
        <div
          className="animate-blob absolute -bottom-40 left-1/4 h-[40vmax] w-[40vmax] rounded-full blur-[120px] [animation-delay:-16s] transition-colors duration-1000"
          style={{ backgroundColor: palette.blob3 }}
        />
      </div>

      {/* Smooth cursor spotlight */}
      {!mobile && (
        <CursorTorch
          color={palette.torchColor}
          secondaryColor={palette.torchSecondary}
        />
      )}

      {/* WebGL2 Aurora curtains */}
      <div className="absolute inset-0">
        <Aurora
          key={`${paletteId}-${theme}`}
          colorStops={
            light
              ? [palette.primary, palette.secondary, palette.tertiary]
              : palette.auroraStops
          }
          amplitude={1.15}
          blend={0.72}
          speed={0.65}
          height={0.48}
          glow={0.45}
          layers={mobile ? 2 : 3}
          brightness={light ? 0.8 : 0.78}
          opacity={light ? 0.55 : 0.65}
          lightMode={light}
          dpr={1}
        />
      </div>

      {/* Subtle architectural grid */}
      <div
        className="grid-bg absolute inset-0 opacity-45"
        style={{
          WebkitMaskImage: 'radial-gradient(ellipse 80% 70% at 50% 35%, #000 25%, transparent 80%)',
          maskImage: 'radial-gradient(ellipse 80% 70% at 50% 35%, #000 25%, transparent 80%)',
        }}
      />

      {/* Aceternity traveling beams */}
      {!light && <BackgroundBeams className="opacity-35" />}

      {/* Interactive constellation particles */}
      <div className="absolute inset-0">
        <Particles
          key={`particles-${paletteId}-${theme}`}
          particleCount={mobile ? 45 : 110}
          particleSpread={11}
          speed={0.11}
          particleColors={palette.particleColors}
          moveParticlesOnHover
          hoverEffect="repel"
          hoverRadius={160}
          particleHoverFactor={1.3}
          particleBaseSize={mobile ? 65 : 80}
          sizeRandomness={1.2}
          connections={!mobile}
          connectionDistance={125}
          drift="up"
          driftSpeed={0.5}
          glow={0.4}
          twinkle={0.45}
          disableRotation={false}
          lightMode={light}
          opacity={light ? 0.6 : 0.78}
          alphaParticles={false}
        />
      </div>

      {/* Center darkening vignette so cards and text stay ultra-readable */}
      <div
        className="absolute inset-0"
        style={{
          background: light
            ? 'radial-gradient(ellipse at center, transparent 60%, rgba(244,246,255,0.75) 100%)'
            : 'radial-gradient(ellipse at center, rgba(5,7,17,0.35) 0%, rgba(4,6,14,0.75) 100%)',
        }}
      />
    </div>
  )
}

export default memo(Background)
