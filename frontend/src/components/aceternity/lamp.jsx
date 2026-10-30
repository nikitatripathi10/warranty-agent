// Source: Aceternity UI registry — components/ui/lamp.tsx (toned down for calm, low-glare reading comfort)
import { motion } from 'motion/react'
import { cn } from '../../lib/utils'

export const LampContainer = ({
  children,
  className,
  color = '#4f8fa8',
  secondaryColor = '#6d72c9',
}) => {
  return (
    <div className={cn('relative flex w-full flex-col items-center justify-start overflow-visible pt-8 pb-6', className)}>
      {/* Subtle ambient lamp projection */}
      <div className="pointer-events-none absolute inset-x-0 top-0 flex h-[340px] sm:h-[380px] items-start justify-center overflow-hidden -z-10" aria-hidden="true">
        <div className="relative flex w-full max-w-4xl items-center justify-center isolate">
          <motion.div
            initial={{ opacity: 0.15, width: '12rem' }}
            animate={{ opacity: 0.35, width: '24rem' }}
            transition={{ delay: 0.1, duration: 1.2, ease: 'easeOut' }}
            style={{
              backgroundImage: `conic-gradient(from 70deg at center top, ${color}, transparent 65%)`,
            }}
            className="absolute inset-auto right-1/2 h-48 w-[24rem]"
          />

          <motion.div
            initial={{ opacity: 0.15, width: '12rem' }}
            animate={{ opacity: 0.35, width: '24rem' }}
            transition={{ delay: 0.1, duration: 1.2, ease: 'easeOut' }}
            style={{
              backgroundImage: `conic-gradient(from 290deg at center top, transparent 35%, ${secondaryColor})`,
            }}
            className="absolute inset-auto left-1/2 h-48 w-[24rem]"
          />

          <div
            className="absolute top-8 h-32 w-72 rounded-full blur-3xl opacity-25"
            style={{
              background: `radial-gradient(circle, ${color} 0%, ${secondaryColor} 70%, transparent 100%)`,
            }}
          />

          <motion.div
            initial={{ width: '10rem', opacity: 0.2 }}
            animate={{ width: '24rem', opacity: 0.45 }}
            transition={{ delay: 0.2, duration: 1.2, ease: 'easeOut' }}
            className="absolute top-[5.5rem] h-[1px] rounded-full"
            style={{
              background: `linear-gradient(to right, transparent, ${color}, ${secondaryColor}, transparent)`,
            }}
          />
        </div>
      </div>

      <div className="relative z-10 flex w-full flex-col items-center px-4">
        {children}
      </div>
    </div>
  )
}
