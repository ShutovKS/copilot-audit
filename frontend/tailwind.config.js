/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Cloud.ru Evolution Authentic Palette
        background: "#131418", // Main Deep Background
        surface: "#1f2126",    // Cards / Panels
        surfaceHover: "#2b2d33", 
        border: "#2d3038",     // Subtle Borders
        
        // Brand Colors
        primary: "#00b67a",    // Evolution Green (CTA)
        primaryHover: "#00a36d",
        secondary: "#7c3aed",  // Evolution Purple (Accents)
        
        // Typography
        text: "#ffffff",       // Primary Text
        muted: "#9ca3af",      // Secondary Text (Gray-400)
        
        // Status Indicators
        error: "#ef4444",
        success: "#00b67a",
        warning: "#f59e0b",
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Menlo', 'monospace'],
      }
    },
  },
  plugins: [],
}