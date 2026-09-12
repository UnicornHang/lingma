/** @type {import('tailwindcss').Config} */
// LingMa 设计系统 - Material 3 风格
// 主色 #5B5FE9, 三级色 #00662B (绿)
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: ['class', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        // === Material 3 主色系 ===
        primary: {
          DEFAULT: '#5B5FE9',
          hover: '#4A4ED8',
          active: '#3D41C7',
          container: '#E0E1FF',
          'on-container': '#14199C',
          fixed: '#DDE0FF',
          'fixed-dim': '#BAC2FF',
          'on-fixed': '#0B156F',
        },
        // === Material 3 次色系 (中性灰) ===
        secondary: {
          DEFAULT: '#5A5C72',
          hover: '#474A5E',
          container: '#E0E1F9',
          'on-container': '#171A2C',
        },
        // === Material 3 三级色 (强调绿) ===
        tertiary: {
          DEFAULT: '#00662B',
          hover: '#005522',
          container: '#9AF6B6',
          'on-container': '#002009',
        },
        // === 语义色 ===
        error: {
          DEFAULT: '#BA1A1A',
          container: '#FFDAD6',
          'on-container': '#410002',
        },
        // === Material 3 Surface 色阶 ===
        surface: {
          DEFAULT: '#FCFBFF',
          dim: '#DCD9E2',
          bright: '#FCFBFF',
          'lowest': '#FFFFFF',
          low: '#F2F3FF',
          DEFAULT: '#EFEDF7',
          high: '#E9E7EF',
          highest: '#E3E2E8',
        },
        // === On-Surface 文字色阶 ===
        'on-surface': '#1C1B1E',
        'on-surface-variant': '#46464F',
        'on-surface-low': '#6B6B73',
        // === Outline ===
        outline: '#777680',
        'outline-variant': '#C7C5D0',

        // === 向后兼容的别名 (老代码继续工作) ===
        accent: {
          DEFAULT: '#F59E0B',
          light: '#FEF3C7',
        },
        success: '#00662B',
        warning: '#7C5800',
        danger: '#BA1A1A',
        info: '#0B6BCB',
      },
      fontFamily: {
        sans: [
          'Inter',
          '"Noto Sans SC"',
          '"PingFang SC"',
          '"Microsoft YaHei"',
          'sans-serif',
        ],
        serif: [
          '"Source Han Serif SC"',
          '"Noto Serif SC"',
          'serif',
        ],
        mono: [
          '"JetBrains Mono"',
          'Consolas',
          'monospace',
        ],
      },
      fontSize: {
        display: ['40px', { lineHeight: '48px', letterSpacing: '-0.5px' }],
        'headline-lg': ['28px', { lineHeight: '36px', letterSpacing: '-0.2px' }],
        'headline-md': ['24px', { lineHeight: '32px' }],
        'headline-sm': ['20px', { lineHeight: '28px' }],
        'body-lg': ['17px', { lineHeight: '26px' }],
        'body-md': ['14px', { lineHeight: '22px' }],
        'body-sm': ['12px', { lineHeight: '18px' }],
        'label-lg': ['14px', { lineHeight: '20px', letterSpacing: '0.1px' }],
        'label-md': ['12px', { lineHeight: '16px', letterSpacing: '0.5px' }],
        'label-sm': ['11px', { lineHeight: '16px', letterSpacing: '0.5px' }],
        'code-md': ['13px', { lineHeight: '20px' }],
        'code-sm': ['11px', { lineHeight: '16px' }],
      },
      spacing: {
        'space-xs': '4px',
        'space-sm': '8px',
        'space-md': '12px',
        'space-lg': '16px',
        'space-xl': '24px',
        'space-2xl': '32px',
        'space-3xl': '48px',
      },
      borderRadius: {
        sm: '2px',
        DEFAULT: '4px',
        md: '6px',
        lg: '8px',
        xl: '12px',
        '2xl': '16px',
        '3xl': '24px',
      },
      boxShadow: {
        'L1-card': '0 1px 3px 0 rgba(31,35,48,0.08), 0 1px 2px 0 rgba(31,35,48,0.06)',
        'L2-popover': '0 4px 12px 0 rgba(31,35,48,0.10), 0 2px 6px 0 rgba(31,35,48,0.06)',
        'L3-modal': '0 12px 32px 0 rgba(31,35,48,0.18), 0 6px 12px 0 rgba(31,35,48,0.10)',
        card: '0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)',
        hover: '0 4px 12px rgba(0,0,0,0.08)',
        modal: '0 20px 50px rgba(0,0,0,0.15)',
      },
      width: {
        sidebar: '240px',
        header: '64px',
        'content-1': '880px',
        'content-2': '1040px',
      },
      height: {
        sidebar: '100vh',
        header: '64px',
      },
      maxWidth: {
        prose: '880px',
      },
    },
  },
  plugins: [],
};