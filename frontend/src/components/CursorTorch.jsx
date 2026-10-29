import { useEffect } from 'react'
import { motion, useMotionValue, useSpring } from 'motion/react'

/**
 * Dynamic cursor-following radiant plasma torch.
 * Reacts smoothly to mouse movement across the entire page,
 * casting an ethereal electric glow on the surrounding dark canvas.
 */
export default function CursorTorch({ color = '#ec4899', secondaryColor = '#06b6d4' }) {
  const mouseX = useMotionValue(-500)
  const mouseY = useMotionValue(-500)

  // Spring physics for organic fluid trailing
  const springX = useSpring(mouseX, { stiffness: 180, damping: 28 })
  const springY = useSpring(mouseY, { stiffness: 180, damping: 28 })

  useEffect(() => {
    const handleMouseMove = (e) => {
      mouseX.set(e.clientX)
      mouseY.set(e.clientY)
    }

    window.addEventListener('mousemove', handleMouseMove, { passive: true })
    return () => window.removeEventListener('mousemove', handleMouseMove)
  }, [mouseX, mouseY])

  return (
    <motion.div
      className="pointer-events-none fixed z-10 size-[420px] rounded-full -translate-x-1/2 -translate-y-1/2 opacity-35 blur-[90px] mix-blend-screen transition-opacity duration-700"
      style={{
        left: springX,
        top: springY,
        background: `radial-gradient(circle, ${color} 0%, ${secondaryColor} 45%, transparent 70%)`,
      }}
      aria-hidden="true"
    />
  )
}
