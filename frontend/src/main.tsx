import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider, App as AntdApp } from 'antd';
import zhCN from 'antd/locale/zh_CN';

import App from './App';
import './styles/globals.css';

// React Query 客户端
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// Ant Design 主题 - Fresh Emerald Studio (v0.2 翡翠版 · 浅色)
const theme = {
  token: {
    colorPrimary: '#0d9488',
    colorPrimaryHover: '#14b8a6',
    colorPrimaryActive: '#0f766e',
    colorPrimaryBg: '#f0fdfa',
    colorPrimaryBgHover: '#ccfbf1',
    colorPrimaryBorder: '#5eead4',
    colorPrimaryBorderHover: '#2dd4bf',
    colorPrimaryText: '#0d9488',
    colorPrimaryTextHover: '#14b8a6',
    colorPrimaryTextActive: '#0f766e',
    colorSuccess: '#10b981',
    colorSuccessHover: '#34d399',
    colorSuccessActive: '#059669',
    colorSuccessBg: '#f0fdf4',
    colorSuccessBgHover: '#dcfce7',
    colorSuccessBorder: '#86efac',
    colorSuccessText: '#059669',
    colorError: '#ef4444',
    colorErrorHover: '#dc2626',
    colorErrorActive: '#b91c1c',
    colorErrorBg: '#fee2e2',
    colorErrorBgHover: '#fecaca',
    colorErrorBorder: '#ef4444',
    colorErrorText: '#dc2626',
    colorWarning: '#d97706',
    colorWarningHover: '#b45309',
    colorWarningBg: '#fef3c7',
    colorWarningText: '#b45309',
    colorInfo: '#0ea5e9',
    colorInfoHover: '#38bdf8',
    colorInfoBg: '#e0f2fe',
    colorInfoText: '#0369a1',
    colorLink: '#0d9488',
    colorLinkHover: '#14b8a6',
    colorLinkActive: '#0f766e',
    colorBgBase: '#ffffff',
    colorTextBase: '#0f172a',
    colorTextSecondary: '#334155',
    colorTextTertiary: '#64748b',
    colorTextQuaternary: '#94a3b8',
    colorBorder: '#cbd5e1',
    colorBorderSecondary: '#e2e8f0',
    borderRadius: 8,
    borderRadiusLG: 12,
    borderRadiusSM: 4,
    fontFamily: 'Plus Jakarta Sans, Inter, "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif',
    fontSize: 14,
    controlHeight: 36,
    boxShadow:
      '0 1px 3px 0 rgba(13,148,136,0.04), 0 1px 2px 0 rgba(15,23,42,0.03)',
    boxShadowSecondary:
      '0 10px 25px -5px rgba(13,148,136,0.08), 0 8px 10px -6px rgba(2,132,199,0.04)',
    wireframe: false,
  },
  components: {
    Layout: {
      headerBg: 'transparent',
      headerHeight: 64,
      headerPadding: '0 32px',
      siderBg: '#ffffff',
      bodyBg: 'rgba(240,253,250,0.5)',
      footerBg: 'transparent',
    },
    Menu: {
      itemBg: 'transparent',
      itemSelectedBg: '#10b981',
      itemSelectedColor: '#ffffff',
      itemHoverBg: '#f0fdf4',
      itemHoverColor: '#0f172a',
      itemBorderRadius: 8,
      itemMarginInline: 4,
      itemActiveBg: '#dcfce7',
      horizontalItemSelectedColor: '#0d9488',
      horizontalItemHoverColor: '#14b8a6',
    },
    Button: {
      primaryShadow: '0 4px 14px rgba(13,148,136,0.30)',
      defaultBg: '#ffffff',
      defaultBorderColor: '#cbd5e1',
      defaultHoverBg: '#f8fafc',
      defaultHoverBorderColor: '#5eead4',
      defaultHoverColor: '#0d9488',
      defaultActiveBg: '#f0fdfa',
      defaultActiveBorderColor: '#2dd4bf',
      fontWeight: 600,
    },
    Card: {
      borderRadiusLG: 12,
    },
    Tag: {
      borderRadiusSM: 9999,
    },
    Input: {
      activeBorderColor: '#14b8a6',
      hoverBorderColor: '#5eead4',
      activeShadow: '0 0 0 3px rgba(20,184,166,0.15)',
    },
    Select: {
      optionSelectedBg: '#ccfbf1',
      optionSelectedColor: '#0f766e',
      optionActiveBg: '#f0fdfa',
    },
    Tabs: {
      itemSelectedColor: '#0d9488',
      itemHoverColor: '#14b8a6',
      itemActiveColor: '#0f766e',
      inkBarColor: '#10b981',
      cardBg: '#ffffff',
    },
    Steps: {
      colorPrimary: '#0d9488',
      finishIconBorderColor: '#10b981',
    },
    Radio: {
      colorPrimary: '#0d9488',
      colorPrimaryHover: '#14b8a6',
      colorPrimaryActive: '#0f766e',
      buttonBg: '#ffffff',
      buttonCheckedBg: '#ccfbf1',
      buttonColor: '#475569',
      buttonCheckedColor: '#0f766e',
    },
    Checkbox: {
      colorPrimary: '#0d9488',
      colorPrimaryHover: '#14b8a6',
      colorPrimaryActive: '#0f766e',
    },
    Switch: {
      colorPrimary: '#10b981',
      colorPrimaryHover: '#34d399',
    },
    Modal: {
      titleColor: '#0f172a',
      colorIcon: '#475569',
      colorIconHover: '#0f172a',
    },
    Form: {
      labelColor: '#0f172a',
    },
    Spin: {
      colorPrimary: '#0d9488',
    },
    Slider: {
      handleColor: '#0d9488',
      trackBg: '#0d9488',
      trackHoverBg: '#14b8a6',
    },
    Pagination: {
      colorPrimary: '#0d9488',
      itemActiveBg: '#f0fdfa',
    },
    Empty: {
      colorTextDisabled: '#94a3b8',
    },
    Tooltip: {
      colorBgSpotlight: '#0f172a',
    },
  },
};

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhCN} theme={theme} modal={{ centered: true }}>
        <AntdApp>
          <BrowserRouter>
            <App />
          </BrowserRouter>
        </AntdApp>
      </ConfigProvider>
    </QueryClientProvider>
  </React.StrictMode>
);