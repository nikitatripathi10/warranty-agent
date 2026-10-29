import { useState, useRef, useCallback } from 'react'
import { motion, useSpring, useMotionValue } from 'motion/react'
import { cn } from '../../lib/utils'

/**
 * 3D Interactive Tilt & Glare Card (React Bits inspired).
 * Tracks cursor movement with spring physics to create an authentic 3D perspective
 * pitch and yaw rotation accompanied by dynamic sheen glare.
 */
export default function TiltCard({
  children,
  className = '',
  maxTilt = 10,
  glare = true,
  glareOpacity = 0.25,
  glareColor = 'rgba(255, 255, 255, 0.65)',
  scaleOnHover = 1.02,
  ...props
}) {
  const cardRef = useRef(null)
  const [isHovered, setIsHovered] = useState(false)

  // Motion values
  const x = useMotionValue(0)
  const y = useMotionValue(0)
  const glareX = useMotionValue(50)
  const glareY = useMotionValue(50)

  // Spring physics for buttery-smooth tilting
  const rotateX = useSpring(x, { stiffness: 240, damping: 22 })
  const rotateY = useSpring(y, { stiffness: 240, damping: 22 })

  const handleMouseMove = useCallback(
    (e) => {
      if (!cardRef.current) return
      const rect = cardRef.current.getBoundingClientRect()
      const clientX = e.clientX - rect.left
      const clientY = e.clientY - rect.top

      const pctX = clientX / rect.width
      const pctY = clientY / rect.height

      // -maxTilt to +maxTilt
      const tiltY = (pctX - 0.5) * (maxTilt * 2)
      const tiltX = (0.5 - pctY) * (maxTilt * 2)

      x.set(tiltX)
      y.set(tiltY)
      glareX.set(pctX * 100)
      glareY.set(pctY * 100)
    },
    [maxTilt, x, y, glareX, glareY]
  )

  const handleMouseEnter = () => setIsHovered(true)

  const handleMouseLeave = () => {
    setIsHovered(false)
    x.set(0)
    y.set(0)
    glareX.set(50)
    glareY.set(50)
  }

  return (
    <div
      ref={cardRef}
      onMouseMove={handleMouseMove}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      className="relative [perspective:1200px]"
      {...props}
    >
      <motion.div
        style={{
          rotateX,
          rotateY,
          transformStyle: 'preserve-3d',
        }}
        animate={{
          scale: isHovered ? scaleOnHover : 1,
        }}
        transition={{ duration: 0.25 }}
        className={cn('relative h-full w-full will-change-transform', className)}
      >
        {children}

        {/* Dynamic Sheen Glare */}
        {glare && (
          <motion.div
            className="pointer-events-none absolute inset-0 rounded-[inherit] overflow-hidden mix-blend-overlay transition-opacity duration-300"
            style={{
              opacity: isHovered ? glareOpacity : 0,
              background: `radial-gradient(circle 380px at ${glareX.get()}% ${glareY.get()}%, ${glareColor}, transparent 80%)`,
            }}
            aria-hidden="true"
          />
        )}
      </motion.div>
    </div>
  )
}
