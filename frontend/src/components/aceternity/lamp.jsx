// Source: Aceternity UI registry — components/ui/lamp.tsx (optimized for content visibility)
import { motion } from 'motion/react'
import { cn } from '../../lib/utils'

/**
 * Atmospheric Aceternity Lamp Stage.
 * Projects dual conic light beams, a central glowing plasma orb,
 * and a razor-thin neon horizon laser beam without clipping or hiding children.
 */
export const LampContainer = ({
  children,
  className,
  color = '#00dfd8',
  secondaryColor = '#ff007a',
}) => {
  return (
    <div className={cn('relative flex w-full flex-col items-center justify-start overflow-visible pt-10 pb-6', className)}>
      {/* Background Lamp Projection (strictly behind content, pointer-events-none) */}
      <div className="pointer-events-none absolute inset-x-0 top-0 flex h-[380px] sm:h-[440px] items-start justify-center overflow-hidden -z-10" aria-hidden="true">
        <div className="relative flex w-full max-w-5xl items-center justify-center isolate">
          {/* Left conic beam */}
          <motion.div
            initial={{ opacity: 0.35, width: '12rem' }}
            animate={{ opacity: 0.85, width: '28rem' }}
            transition={{ delay: 0.1, duration: 1.2, ease: 'easeInOut' }}
            style={{
              backgroundImage: `conic-gradient(from 70deg at center top, ${color}, transparent 60%)`,
            }}
            className="absolute inset-auto right-1/2 h-52 w-[28rem] opacity-75"
          />

          {/* Right conic beam */}
          <motion.div
            initial={{ opacity: 0.35, width: '12rem' }}
            animate={{ opacity: 0.85, width: '28rem' }}
            transition={{ delay: 0.1, duration: 1.2, ease: 'easeInOut' }}
            style={{
              backgroundImage: `conic-gradient(from 290deg at center top, transparent 40%, ${secondaryColor})`,
            }}
            className="absolute inset-auto left-1/2 h-52 w-[28rem] opacity-75"
          />

          {/* Ambient glow sphere */}
          <div
            className="absolute top-10 h-36 w-80 rounded-full blur-3xl opacity-60"
            style={{
              background: `radial-gradient(circle, ${color} 0%, ${secondaryColor} 70%, transparent 100%)`,
            }}
          />

          {/* Central glowing core ball */}
          <motion.div
            initial={{ width: '8rem', opacity: 0.4 }}
            animate={{ width: '22rem', opacity: 0.8 }}
            transition={{ delay: 0.15, duration: 1.2, ease: 'easeInOut' }}
            className="absolute top-24 h-24 rounded-full blur-2xl"
            style={{
              background: `linear-gradient(to right, ${color}, ${secondaryColor})`,
            }}
          />

          {/* Horizontal Neon Laser Line */}
          <motion.div
            initial={{ width: '10rem', opacity: 0.3 }}
            animate={{ width: '32rem', opacity: 1 }}
            transition={{ delay: 0.2, duration: 1.2, ease: 'easeInOut' }}
            className="absolute top-[6.5rem] h-[2px] rounded-full"
            style={{
              background: `linear-gradient(to right, ${color}, #ffffff 50%, ${secondaryColor})`,
              boxShadow: `0 0 20px ${color}, 0 0 36px ${secondaryColor}`,
            }}
          />
        </div>
      </div>

      {/* Children content (fully interactive, natural flow, completely visible) */}
      <div className="relative z-10 flex w-full flex-col items-center px-4">
        {children}
      </div>
    </div>
  )
}
