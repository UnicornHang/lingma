/** @type {import('tailwindcss').Config} */
// LingMa 设计系统 - Fresh Emerald Studio (翡翠版)
// 主色: Teal #0D9488 / Emerald #059669 / Sky #0284C7
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: ['class', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        // === Primary Spectrum: Teal & Emerald (lighter) ===
        primary: {
          DEFAULT: '#0d9488',         // Standard teal
          hover: '#14b8a6',
          active: '#0f766e',
          container: '#ccfbf1',       // Soft teal backdrop
          'on-container': '#134e4a',
          fixed: '#f0fdfa',           // Very soft mint (was teal-300, too vivid)
          'fixed-dim': '#ccfbf1',
          'on-fixed': '#042f2e',
          // 兼容别名
          'vibrant': '#10b981',       // Emerald accent
        },
        // === Secondary Spectrum: Sky (lighter) ===
        secondary: {
          DEFAULT: '#0ea5e9',         // Sky blue
          hover: '#38bdf8',
          container: '#e0f2fe',       // Soft sky backdrop
          'on-container': '#075985',
          fixed: '#bae6fd',
          'fixed-dim': '#7dd3fc',
          'on-fixed-variant': '#0369a1',
        },
        // === Tertiary Spectrum: Green (lighter) ===
        tertiary: {
          DEFAULT: '#10b981',         // Fresh emerald
          hover: '#34d399',
          container: '#d1fae5',
          'on-container': '#065f46',
        },
        // === 语义色 ===
        error: {
          DEFAULT: '#ef4444',
          container: '#fee2e2',
          'on-container': '#7f1d1d',
        },
        // === Surface 色阶 (Fresh Emerald) ===
        surface: {
          DEFAULT: '#ffffff',
          dim: '#f0fdf4',             // mint surface-dim
          bright: '#ffffff',
          lowest: '#ffffff',
          low: '#f0fdf4',             // mint surface-container-low
          container: '#e6f7ef',       // mint surface-container
          high: '#dcfce7',            // mint surface-container-high
          highest: '#bbf7d0',         // mint surface-container-highest
        },
        // === Background ===
        background: '#f8fafc',        // Crisp daylight slate-white
        // === On-Surface 文字色阶（提深） ===
        'on-surface': '#0f172a',          // Heading obsidian
        'on-surface-variant': '#334155',  // Body slate-700 (was slate-600)
        'on-surface-low': '#64748b',      // slate-600 (was slate-400)
        // === Outline（提深） ===
        outline: '#64748b',
        'outline-variant': '#cbd5e1',

        // === 向后兼容的别名 (老代码继续工作) ===
        accent: {
          DEFAULT: '#F59E0B',
          light: '#FEF3C7',
        },
        success: '#059669',
        warning: '#d97706',
        danger: '#ef4444',
        info: '#0284c7',
      },
      fontFamily: {
        sans: [
          'Plus Jakarta Sans',
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
        display: ['40px', { lineHeight: '48px', letterSpacing: '-0.02em' }],
        'headline-lg': ['24px', { lineHeight: '32px', letterSpacing: '-0.01em' }],
        'headline-md': ['20px', { lineHeight: '28px', letterSpacing: '-0.005em' }],
        'headline-sm': ['16px', { lineHeight: '24px' }],
        'body-xl': ['18px', { lineHeight: '32px', letterSpacing: '0.01em' }],
        'body-lg': ['16px', { lineHeight: '28px', letterSpacing: '0.005em' }],
        'body-md': ['14px', { lineHeight: '22px' }],
        'body-sm': ['12px', { lineHeight: '18px', letterSpacing: '0.01em' }],
        'label-lg': ['14px', { lineHeight: '20px', letterSpacing: '0.01em' }],
        'label-md': ['12px', { lineHeight: '16px', letterSpacing: '0.02em' }],
        'label-sm': ['11px', { lineHeight: '14px', letterSpacing: '0.03em' }],
        'code-md': ['13px', { lineHeight: '20px' }],
        'code-sm': ['11px', { lineHeight: '16px' }],
      },
      spacing: {
        'space-xs': '4px',
        'space-sm': '8px',
        'space-md': '16px',
        'space-lg': '24px',
        'space-xl': '32px',
        'space-2xl': '48px',
        'space-3xl': '64px',
      },
      borderRadius: {
        sm: '4px',
        DEFAULT: '8px',
        md: '8px',
        lg: '12px',
        xl: '16px',
        '2xl': '24px',
        full: '9999px',
      },
      boxShadow: {
        // Fresh Emerald Elevation: Teal-Infused Hairlines (lighter)
        'L1-card': '0 1px 3px 0 rgba(20,184,166,0.05), 0 1px 2px 0 rgba(15,23,42,0.03)',
        'L2-popover': '0 10px 25px -5px rgba(20,184,166,0.10), 0 8px 10px -6px rgba(14,165,233,0.04)',
        'L3-modal': '0 20px 35px -10px rgba(15,23,42,0.12)',
        card: '0 1px 3px 0 rgba(20,184,166,0.05), 0 1px 2px 0 rgba(15,23,42,0.03)',
        hover: '0 4px 14px rgba(20,184,166,0.12)',
        modal: '0 20px 50px rgba(15,23,42,0.15)',
        'emerald-glow': '0 4px 14px rgba(20,184,166,0.30)',
        'emerald-soft': '0 2px 8px rgba(16,185,129,0.08)',
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
      backgroundImage: {
        'emerald-gradient': 'linear-gradient(135deg, #14b8a6 0%, #10b981 100%)',
        'teal-emerald': 'linear-gradient(to bottom right, #f0fdf4, #ccfbf1)',
      },
    },
  },
  plugins: [],
};
