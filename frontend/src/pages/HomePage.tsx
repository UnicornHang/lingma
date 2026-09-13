import { Link } from 'react-router-dom';
import { ArrowRight, FileText, Shield, ShieldCheck } from 'lucide-react';
import logo from '../images/logo.png';

export default function HomePage() {
  return (
    <div className="relative w-full h-full flex items-center justify-center overflow-hidden">
      {/* Background radial */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            'radial-gradient(circle at 50% 45%, rgba(5,150,105,0.10), transparent 55%)',
        }}
      />

      <div className="flex flex-col items-center text-center max-w-[820px] px-8 relative z-10">
        {/* Logo with glow */}
        <div className="relative">
          <div className="absolute inset-0 rounded-3xl bg-primary/20 blur-2xl" />
          <div className="relative h-24 w-24 rounded-3xl bg-white flex items-center justify-center shadow-[0_8px_32px_rgba(5,150,105,0.35)] overflow-hidden">
            <img src={logo} alt="织梦 ZhiMeng" className="h-full w-full object-contain" />
          </div>
        </div>

        <h1 className="text-display font-bold tracking-tight mt-8 bg-gradient-to-r from-[#00685f] via-[#059669] to-[#10b981] bg-clip-text text-transparent">
          织梦 · ZhiMeng
        </h1>
        <p className="text-body-lg text-on-surface-variant mt-2">
          你的本地 AI 小说创作搭档
        </p>

        <div className="flex items-center gap-1 px-3 py-1.5 mt-3 rounded-full bg-surface-container-lowest border border-outline-variant/40">
          <span className="dot-pulse" />
          <span className="font-code-sm text-on-surface-variant">
            v0.2 本地版 · 离线 RAG + 协作 Agent 就绪
          </span>
        </div>

        <div className="flex items-center gap-4 mt-10">
          <Link
            to="/works"
            className="flex items-center gap-2 px-6 py-3 bg-primary text-white rounded-lg text-label-md font-medium shadow-[0_4px_12px_rgba(5,150,105,0.35)] hover:bg-primary-hover transition-all"
          >
            <span>进入作品库</span>
            <ArrowRight size={20} />
          </Link>
          <Link
            to="/help"
            className="flex items-center gap-2 px-6 py-3 bg-surface-container-lowest border border-outline-variant/50 text-on-surface rounded-lg text-label-md font-medium hover:bg-surface-container-high transition-all"
          >
            <FileText size={20} />
            <span>查看文档</span>
          </Link>
        </div>

        {/* Config hint */}
        <div className="mt-8 px-4 py-3 rounded-xl bg-surface-container-high/60 border border-outline-variant/40 flex items-center gap-3 max-w-[640px]">
          <ShieldCheck size={20} className="text-tertiary" />
          <div className="flex flex-col items-start text-left">
            <span className="text-label-md text-on-surface">还没有配置 LLM API Key？</span>
            <span className="text-body-sm text-on-surface-variant">
              前往「系统设置 → LLM API 配置」即可接入 OpenAI / Anthropic / DeepSeek / Ollama
            </span>
          </div>
          <Link
            to="/settings/llm"
            className="ml-auto px-3 py-1.5 rounded-lg bg-primary-container text-on-primary-container text-label-sm font-semibold hover:opacity-90"
          >
            前往设置 →
          </Link>
        </div>

        {/* Quick stats */}
        <div className="flex items-center gap-12 mt-10">
          <div className="flex flex-col items-center">
            <span className="text-display font-bold text-primary">6</span>
            <span className="text-label-sm text-on-surface-variant mt-1">协作 Agent</span>
          </div>
          <div className="w-px h-10 bg-outline-variant/60" />
          <div className="flex flex-col items-center">
            <span className="text-display font-bold text-primary">100%</span>
            <span className="text-label-sm text-on-surface-variant mt-1">本地运行</span>
          </div>
          <div className="w-px h-10 bg-outline-variant/60" />
          <div className="flex flex-col items-center">
            <span className="text-display font-bold text-primary">0</span>
            <span className="text-label-sm text-on-surface-variant mt-1">云端上传</span>
          </div>
        </div>

        {/* Privacy seal */}
        <div className="mt-12 flex items-center gap-2 text-body-sm text-on-surface-low">
          <Shield size={14} />
          <span>所有作品、API Key 与对话均加密存储于本机</span>
        </div>
      </div>
    </div>
  );
}