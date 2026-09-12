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

// Ant Design 主题 - Material 3 对齐
const theme = {
  token: {
    colorPrimary: '#5B5FE9',
    colorSuccess: '#00662B',
    colorError: '#BA1A1A',
    colorWarning: '#7C5800',
    colorInfo: '#0B6BCB',
    colorBgBase: '#FCFBFF',
    colorTextBase: '#1C1B1E',
    borderRadius: 6,
    borderRadiusLG: 12,
    borderRadiusSM: 4,
    fontFamily: 'Inter, "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif',
    fontSize: 14,
    controlHeight: 36,
    boxShadow:
      '0 1px 3px 0 rgba(31,35,48,0.08), 0 1px 2px 0 rgba(31,35,48,0.06)',
    boxShadowSecondary:
      '0 4px 12px 0 rgba(31,35,48,0.10), 0 2px 6px 0 rgba(31,35,48,0.06)',
  },
  components: {
    Layout: {
      headerBg: 'transparent',
      headerHeight: 64,
      headerPadding: '0 32px',
      siderBg: '#F2F3FF',
      bodyBg: '#F2F3FF',
    },
    Menu: {
      itemBg: 'transparent',
      itemSelectedBg: '#E0E1FF',
      itemSelectedColor: '#14199C',
      itemHoverBg: '#E9E7EF',
      itemBorderRadius: 8,
      itemMarginInline: 4,
    },
    Button: {
      primaryShadow: '0 4px 12px rgba(91,95,233,0.35)',
    },
    Card: {
      borderRadiusLG: 12,
    },
    Tag: {
      borderRadiusSM: 4,
    },
  },
};

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhCN} theme={theme}>
        <AntdApp>
          <BrowserRouter>
            <App />
          </BrowserRouter>
        </AntdApp>
      </ConfigProvider>
    </QueryClientProvider>
  </React.StrictMode>
);