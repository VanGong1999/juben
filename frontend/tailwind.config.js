/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: '#14181F',
          soft: '#2A3140',
          muted: '#5C6575',
          faint: '#8B93A3',
        },
        pearl: {
          DEFAULT: '#FAF9F7',
          soft: '#F3F1ED',
          card: '#FFFefb',
          line: '#E6E2DB',
        },
        atelier: {
          teal: '#0D5C63',
          'teal-mid': '#147A82',
          'teal-soft': '#E4F2F3',
          gold: '#B8956C',
          'gold-soft': '#F5EDE3',
          slate: '#3D4A5C',
        },
        'studio-teal': '#0D5C63',
        'studio-teal-soft': '#E4F2F3',
        'studio-teal-deep': '#094247',
        'studio-amber': '#B8956C',
        'studio-amber-soft': '#F5EDE3',
        'studio-line': '#E6E2DB',
        paper: {
          DEFAULT: '#FAF9F7',
          cool: '#F3F1ED',
          white: '#FFFefb',
        },
        studio: {
          teal: '#0D5C63',
          'teal-soft': '#E4F2F3',
          'teal-deep': '#094247',
          amber: '#B8956C',
          'amber-soft': '#F5EDE3',
          line: '#E6E2DB',
        },
        black: {
          DEFAULT: '#14181F',
          50: '#FAF9F7',
          100: '#F3F1ED',
          200: '#E6E2DB',
          300: '#D4D4D4',
          400: '#A3A3A3',
          500: '#737373',
          600: '#5C6575',
          700: '#404040',
          800: '#2A3140',
          900: '#14181F',
          950: '#0A0C10',
        },
        white: { DEFAULT: '#FFFFFF' },
      },
      fontFamily: {
        display: ['"Cormorant Garamond"', 'Georgia', 'serif'],
        sans: ['"Plus Jakarta Sans"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'Menlo', 'monospace'],
      },
      boxShadow: {
        atelier: '0 1px 0 rgba(20,24,31,0.04), 0 12px 32px rgba(20,24,31,0.06)',
        'atelier-lg': '0 2px 4px rgba(20,24,31,0.03), 0 24px 48px rgba(13,92,99,0.08)',
        'atelier-inset': 'inset 0 1px 0 rgba(255,255,255,0.7)',
        studio: '0 1px 0 rgba(20,24,31,0.04), 0 12px 32px rgba(20,24,31,0.06)',
        'studio-lg': '0 2px 4px rgba(20,24,31,0.03), 0 24px 48px rgba(13,92,99,0.08)',
      },
      backgroundImage: {
        'atelier-mesh':
          'radial-gradient(ellipse 90% 60% at 10% -20%, rgba(13,92,99,0.09), transparent 55%), radial-gradient(ellipse 70% 50% at 100% 0%, rgba(184,149,108,0.08), transparent 50%), linear-gradient(160deg, #FAF9F7 0%, #F0EEF2 48%, #E8F0F1 100%)',
        'studio-mesh':
          'radial-gradient(ellipse 90% 60% at 10% -20%, rgba(13,92,99,0.09), transparent 55%), radial-gradient(ellipse 70% 50% at 100% 0%, rgba(184,149,108,0.08), transparent 50%), linear-gradient(160deg, #FAF9F7 0%, #F0EEF2 48%, #E8F0F1 100%)',
        'atelier-shine':
          'linear-gradient(135deg, rgba(255,254,251,0.9) 0%, rgba(228,242,243,0.5) 100%)',
      },
      animation: {
        'fade-in': 'fadeIn 0.45s cubic-bezier(0.22,1,0.36,1)',
        'slide-up': 'slideUp 0.5s cubic-bezier(0.22,1,0.36,1)',
        'stagger-in': 'fadeIn 0.5s cubic-bezier(0.22,1,0.36,1) both',
        'progress-pulse': 'progressPulse 2s ease-in-out infinite',
        float: 'float 6s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        progressPulse: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-6px)' },
        },
      },
    },
  },
  plugins: [],
};
