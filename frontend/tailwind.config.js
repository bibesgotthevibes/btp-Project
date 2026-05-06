/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      colors: {
        primary: {
          50:  '#f5f3ff',
          100: '#ede9fe',
          200: '#ddd6fe',
          500: '#6C4DF6',
          600: '#5b3de5',
          700: '#4c32c4',
        },
      },
      boxShadow: {
        card: '0 2px 16px 0 rgba(108,77,246,0.07)',
      },
    },
  },
  plugins: [],
}
