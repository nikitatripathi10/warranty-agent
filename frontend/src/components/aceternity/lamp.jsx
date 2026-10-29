// Source: Aceternity UI registry — components/ui/lamp.tsx (converted to JSX)
import { motion } from 'motion/react'
import { cn } from '../../lib/utils'

export const LampContainer = ({
  children,
  className,
  color = '#00dfd8',
  secondaryColor = '#ff007a',
}) => {
  return (
    <div
      className={cn(
        'relative flex min-h-[460px] sm:min-h-[520px] flex-col items-center justify-center overflow-hidden w-full rounded-2xl z-0 pointer-events-none pt-12 pb-24',
        className
      )}
    >
      <div className="relative flex w-full flex-1 scale-y-110 sm:scale-y-125 items-center justify-center isolate z-0">
        {/* Left conic beam */}
        <motion.div
          initial={{ opacity: 0.5, width: '12rem' }}
          whileInView={{ opacity: 1, width: '30rem' }}
          transition={{ delay: 0.2, duration: 1.1, ease: 'easeInOut' }}
          style={{
            backgroundImage: `conic-gradient(from 70deg at center top, ${color}, transparent, transparent)`,
          }}
          className="absolute inset-auto right-1/2 h-56 overflow-visible w-[30rem] text-white"
        >
          <div className="absolute w-full left-0 bg-bg h-40 bottom-0 z-20 [mask-image:linear-gradient(to_top,white,transparent)]" />
          <div className="absolute w-40 h-full left-0 bg-bg bottom-0 z-20 [mask-image:linear-gradient(to_right,white,transparent)]" />
        </motion.div>

        {/* Right conic beam */}
        <motion.div
          initial={{ opacity: 0.5, width: '12rem' }}
          whileInView={{ opacity: 1, width: '30rem' }}
          transition={{ delay: 0.2, duration: 1.1, ease: 'easeInOut' }}
          style={{
            backgroundImage: `conic-gradient(from 290deg at center top, transparent, transparent, ${secondaryColor})`,
          }}
          className="absolute inset-auto left-1/2 h-56 w-[30rem] text-white"
        >
          <div className="absolute w-40 h-full right-0 bg-bg bottom-0 z-20 [mask-image:linear-gradient(to_left,white,transparent)]" />
          <div className="absolute w-full right-0 bg-bg h-40 bottom-0 z-20 [mask-image:linear-gradient(to_top,white,transparent)]" />
        </motion.div>

        {/* Ambient glow patches */}
        <div className="absolute top-1/2 h-44 w-full translate-y-12 scale-x-150 bg-bg blur-2xl" />
        <div className="absolute top-1/2 z-50 h-44 w-full bg-transparent opacity-10 backdrop-blur-md" />
        <div
          className="absolute inset-auto z-50 h-32 w-[26rem] -translate-y-1/2 rounded-full opacity-65 blur-3xl"
          style={{ backgroundColor: color }}
        />

        {/* Central glowing core ball */}
        <motion.div
          initial={{ width: '8rem' }}
          whileInView={{ width: '20rem' }}
          transition={{ delay: 0.2, duration: 1.1, ease: 'easeInOut' }}
          className="absolute inset-auto z-30 h-32 w-80 -translate-y-[5.5rem] rounded-full blur-2xl opacity-75"
          style={{
            background: `linear-gradient(to right, ${color}, ${secondaryColor})`,
          }}
        />

        {/* Horizontal Laser Line */}
        <motion.div
          initial={{ width: '12rem' }}
          whileInView={{ width: '34rem' }}
          transition={{ delay: 0.2, duration: 1.1, ease: 'easeInOut' }}
          className="absolute inset-auto z-50 h-0.5 w-[34rem] -translate-y-[6.5rem]"
          style={{
            background: `linear-gradient(to right, ${color}, #ffffff, ${secondaryColor})`,
            boxShadow: `0 0 24px ${color}, 0 0 48px ${secondaryColor}`,
          }}
        />

        <div className="absolute inset-auto z-40 h-40 w-full -translate-y-[12rem] bg-bg" />
      </div>

      <div className="relative z-50 pointer-events-auto flex -translate-y-48 sm:-translate-y-52 flex-col items-center px-4 w-full">
        {children}
      </div>
    </div>
  )
}
