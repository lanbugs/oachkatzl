/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#f0f4ff',
          100: '#dce6ff',
          500: '#4f6ef7',
          600: '#3a54d9',
          700: '#2d42b8',
          900: '#1a2570',
        },
      },
    },
  },
  plugins: [require('@tailwindcss/forms')],
}
