import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

/** shadcn-style class merger used by the Magic UI / Aceternity components. */
export function cn(...inputs) {
  return twMerge(clsx(inputs))
}

