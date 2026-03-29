/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      fontSize: {
        // WCAG 2.1 AA 準拠: 高齢者向けに基準フォントサイズを拡張
        'base': ['1.0625rem', { lineHeight: '1.75' }],  // 17px
        'lg':   ['1.125rem',  { lineHeight: '1.75' }],  // 18px
        'xl':   ['1.25rem',   { lineHeight: '1.75' }],  // 20px
        '2xl':  ['1.5rem',    { lineHeight: '1.4'  }],  // 24px
        '3xl':  ['1.875rem',  { lineHeight: '1.4'  }],  // 30px
        '4xl':  ['2.25rem',   { lineHeight: '1.2'  }],  // 36px
      },
    },
  },
  plugins: [],
}
