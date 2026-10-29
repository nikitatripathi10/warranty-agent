import { memo } from 'react'
import Aurora from './reactbits/Aurora'
import Particles from './reactbits/Particles'
import { BackgroundBeams } from './aceternity/background-beams'
import CursorTorch from './CursorTorch'
import { ANIMATION_PALETTES } from '../lib/animation-theme'
import { useIsMobile } from '../lib/hooks'

/**
 * Highly interactive futuristic background:
 *  1. Ambient Plasma Blobs with dynamic color physics
 *  2. Interactive Cursor Torch (Motion spring follower)
 *  3. WebGL2 Aurora Curtains with shifting stops
 *  4. High-tech Cyber Grid with subtle scanline
 *  5. Aceternity Traveling Background Beams
 *  6. Connected Repulsion Particle Mesh
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
      {/* Deep foundation gradient */}
      <div
        className="absolute inset-0"
        style={{
          background: light
            ? 'radial-gradient(120% 80% at 50% -10%, #fdf2f8 0%, #f3f4ff 55%, #eef2ff 100%)'
            : 'radial-gradient(120% 80% at 50% -10%, #170420 0%, #080718 50%, #03040b 100%)',
        }}
      />

      {/* Dynamic Fluid Plasma Blobs in vibrant new colors */}
      <div className={`absolute inset-0 ${light ? 'opacity-35' : 'opacity-75'} transition-opacity duration-700`}>
        <div
          className="animate-blob absolute -top-36 -left-28 h-[48vmax] w-[48vmax] rounded-full blur-[115px] transition-colors duration-1000"
          style={{ backgroundColor: palette.blob1 }}
        />
        <div
          className="animate-blob absolute top-1/4 -right-36 h-[44vmax] w-[44vmax] rounded-full blur-[125px] [animation-delay:-8s] transition-colors duration-1000"
          style={{ backgroundColor: palette.blob2 }}
        />
        <div
          className="animate-blob absolute -bottom-48 left-1/3 h-[42vmax] w-[42vmax] rounded-full blur-[120px] [animation-delay:-16s] transition-colors duration-1000"
          style={{ backgroundColor: palette.blob3 }}
        />
      </div>

      {/* Interactive Cursor Plasma Torch (Smooth spring mouse glow) */}
      {!mobile && (
        <CursorTorch
          color={palette.torchColor}
          secondaryColor={palette.torchSecondary}
        />
      )}

      {/* WebGL2 Aurora Ribbons with new dynamic palette stops */}
      <div className="absolute inset-0">
        <Aurora
          key={`${paletteId}-${theme}`}
          colorStops={
            light
              ? [palette.primary, palette.secondary, palette.tertiary]
              : palette.auroraStops
          }
          amplitude={1.35}
          blend={0.65}
          speed={0.9}
          height={0.52}
          glow={0.8}
          layers={mobile ? 2 : 3}
          brightness={light ? 0.95 : 1.2}
          opacity={light ? 0.75 : 0.92}
          lightMode={light}
          dpr={1}
        />
      </div>

      {/* Futuristic Cyber Grid with radial vignette mask */}
      <div
        className="grid-bg absolute inset-0 opacity-60"
        style={{
          WebkitMaskImage: 'radial-gradient(ellipse 75% 65% at 50% 35%, #000 20%, transparent 75%)',
          maskImage: 'radial-gradient(ellipse 75% 65% at 50% 35%, #000 20%, transparent 75%)',
        }}
      />

      {/* Aceternity Background Beams */}
      {!light && <BackgroundBeams className="opacity-55" />}

      {/* Interactive Particle Mesh with Repel & Click Bursts */}
      <div className="absolute inset-0">
        <Particles
          key={`particles-${paletteId}-${theme}`}
          particleCount={mobile ? 60 : 160}
          particleSpread={11}
          speed={0.14}
          particleColors={palette.particleColors}
          moveParticlesOnHover
          hoverEffect="repel"
          hoverRadius={180}
          particleHoverFactor={1.5}
          particleBaseSize={mobile ? 70 : 95}
          sizeRandomness={1.3}
          connections={!mobile}
          connectionDistance={130}
          clickBurst
          drift="up"
          driftSpeed={0.7}
          glow={0.8}
          twinkle={0.55}
          disableRotation={false}
          lightMode={light}
          opacity={light ? 0.8 : 1}
          alphaParticles={false}
        />
      </div>

      {/* Subtle outer vignette */}
      <div
        className="absolute inset-0"
        style={{
          background: light
            ? 'radial-gradient(ellipse at center, transparent 55%, rgba(243,244,255,0.85) 100%)'
            : 'radial-gradient(ellipse at center, transparent 50%, rgba(2,3,10,0.78) 100%)',
        }}
      />
    </div>
  )
}

export default memo(Background)
