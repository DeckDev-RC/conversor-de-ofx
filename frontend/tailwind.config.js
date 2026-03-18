/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/renderer/**/*.{tsx,ts,html}'],
  theme: {
    extend: {
      colors: {
        nf: {
          red: '#FF7A90',
          'red-hover': '#FF96A6',
          'red-dark': '#C84A64',
        },
        brand: {
          gold: '#8B90A6',
          amber: '#A6B1FF',
          bronze: '#5E6AD2',
          moss: '#11131A',
          pine: '#090B10',
          iris: '#7C89FF',
        },
        surface: {
          50: '#05060A',
          100: '#07090D',
          200: '#0B0D12',
          300: '#10131A',
          400: '#171B24',
          500: '#1E2431',
          600: '#2A3143',
          700: '#3A435A',
          800: '#55607A',
        },
        text: {
          primary: '#F7F8FA',
          secondary: 'rgba(247, 248, 250, 0.72)',
          muted: 'rgba(247, 248, 250, 0.46)',
          disabled: 'rgba(247, 248, 250, 0.28)',
        },
        accent: {
          green: '#5CD6A3',
          'green-dim': '#3DA378',
          red: '#FF7A90',
          'red-dim': '#C84A64',
          blue: '#82A0FF',
          purple: '#A9A1FF',
          yellow: '#E8C071',
          orange: '#FFB86B',
        },
      },
      fontFamily: {
        sans: ['"Outfit"', 'system-ui', 'sans-serif'],
        display: ['"Outfit"', 'system-ui', 'sans-serif'],
        mono: ['SF Mono', 'Cascadia Code', 'Consolas', 'Menlo', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.625rem', { lineHeight: '0.875rem', letterSpacing: '0.02em' }],
      },
      borderRadius: {
        nf: '8px',
        'nf-md': '12px',
        'nf-lg': '16px',
        'nf-xl': '20px',
        'nf-pill': '999px',
      },
      boxShadow: {
        'nf': '0 1px 2px rgba(0, 0, 0, 0.24)',
        'nf-md': '0 12px 40px rgba(0, 0, 0, 0.28)',
        'nf-lg': '0 24px 80px rgba(0, 0, 0, 0.38)',
        'nf-glow': '0 0 40px rgba(130, 160, 255, 0.12)',
        'nf-inner': 'inset 0 1px 0 rgba(255, 255, 255, 0.05)',
        'nf-ring': '0 0 0 1px rgba(255, 255, 255, 0.07)',
      },
      backdropBlur: {
        apple: '28px',
        'apple-lg': '56px',
      },
      animation: {
        'fade-in': 'fadeIn 0.4s cubic-bezier(0.2, 0, 0, 1)',
        'slide-up': 'slideUp 0.5s cubic-bezier(0.2, 0, 0, 1)',
        'scale-in': 'scaleIn 0.35s cubic-bezier(0.2, 0, 0, 1)',
        'pulse-red': 'pulseRed 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        shimmer: 'shimmer 2s linear infinite',
        'glow-pulse': 'glowPulse 3s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        scaleIn: {
          '0%': { opacity: '0', transform: 'scale(0.985)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        pulseRed: {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(255, 122, 144, 0.3)' },
          '50%': { boxShadow: '0 0 0 6px rgba(255, 122, 144, 0)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        glowPulse: {
          '0%, 100%': { opacity: '0.35' },
          '50%': { opacity: '0.72' },
        },
      },
      transitionTimingFunction: {
        apple: 'cubic-bezier(0.2, 0, 0, 1)',
        'apple-bounce': 'cubic-bezier(0.34, 1.56, 0.64, 1)',
      },
    },
  },
  plugins: [],
}
