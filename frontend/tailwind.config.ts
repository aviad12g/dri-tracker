import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Sophisticated dark palette
        bg: {
          primary: '#09090b',
          secondary: '#0c0c0e',
          tertiary: '#111113',
          elevated: '#18181b',
          hover: '#1f1f23',
        },
        border: {
          subtle: 'rgba(255, 255, 255, 0.06)',
          DEFAULT: 'rgba(255, 255, 255, 0.08)',
          strong: 'rgba(255, 255, 255, 0.12)',
        },
        text: {
          primary: '#fafafa',
          secondary: '#a1a1aa',
          tertiary: '#71717a',
          quaternary: '#52525b',
        },
        accent: {
          DEFAULT: '#f59e0b',
          hover: '#fbbf24',
          muted: 'rgba(245, 158, 11, 0.15)',
        },
        success: '#10b981',
        warning: '#f59e0b',
        danger: '#ef4444',
        info: '#3b82f6',
        // Chart colors
        chart: {
          1: '#f59e0b',
          2: '#8b5cf6',
          3: '#06b6d4',
          4: '#10b981',
          5: '#ec4899',
        },
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'system-ui', 'sans-serif'],
        display: ['Outfit', '-apple-system', 'BlinkMacSystemFont', 'system-ui', 'sans-serif'],
        mono: ['IBM Plex Mono', 'SF Mono', 'monospace'],
      },
      fontSize: {
        'xxs': '10px',
      },
      borderRadius: {
        'xl': '12px',
        '2xl': '16px',
        '3xl': '24px',
      },
      boxShadow: {
        'glow': '0 0 40px -10px rgba(245, 158, 11, 0.3)',
        'glow-sm': '0 0 20px -5px rgba(245, 158, 11, 0.2)',
        'card': '0 4px 24px -4px rgba(0, 0, 0, 0.5)',
        'card-hover': '0 8px 40px -8px rgba(0, 0, 0, 0.7)',
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-out forwards',
        'slide-up': 'slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards',
        'slide-down': 'slideDown 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards',
        'scale-in': 'scaleIn 0.2s ease-out forwards',
        'pulse-soft': 'pulse-soft 2s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        slideUp: {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        slideDown: {
          from: { opacity: '0', transform: 'translateY(-8px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        scaleIn: {
          from: { opacity: '0', transform: 'scale(0.96)' },
          to: { opacity: '1', transform: 'scale(1)' },
        },
        'pulse-soft': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.6' },
        },
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
}
export default config
