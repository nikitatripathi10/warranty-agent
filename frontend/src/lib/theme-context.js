import { createContext, useContext } from 'react'

export const ThemeContext = createContext('dark')
export const useThemeValue = () => useContext(ThemeContext)

