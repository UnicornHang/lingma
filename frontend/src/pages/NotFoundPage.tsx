import { Link } from 'react-router-dom';
import { ArrowLeft, Search } from 'lucide-react';

export default function NotFoundPage() {
  return (
    <div className="flex items-center justify-center h-full bg-surface-container-low">
      <div className="flex flex-col items-center text-center max-w-md px-8">
        {/* Big 404 with gradient */}
        <div className="relative">
          <div className="absolute inset-0 rounded-3xl bg-primary/20 blur-2xl" />
          <div className="relative text-[140px] font-bold text-primary leading-none tracking-tighter">
            404
          </div>
        </div>

        <h1 className="text-headline-lg font-bold text-on-surface mt-6">
          页面走丢了
        </h1>
        <p className="text-body-md text-on-surface-variant mt-2">
          你访问的页面不存在，或者它去了另一个故事线。
        </p>

        <div className="flex items-center gap-3 mt-6">
          <Link
            to="/"
            className="flex items-center gap-2 px-6 py-3 bg-primary text-white rounded-lg text-label-md font-medium shadow-[0_4px_12px_rgba(91,95,233,0.35)] hover:bg-primary-hover transition-all"
          >
            <ArrowLeft size={18} />
            <span>返回首页</span>
          </Link>
          <Link
            to="/works"
            className="flex items-center gap-2 px-6 py-3 bg-surface-container-lowest border border-outline-variant/50 text-on-surface rounded-lg text-label-md font-medium hover:bg-surface-container-high transition-all"
          >
            <Search size={18} />
            <span>查看作品库</span>
          </Link>
        </div>

        <p className="text-body-sm text-on-surface-low mt-8">
          错误代码 <code className="font-code-sm">404 · NOT_FOUND</code>
        </p>
      </div>
    </div>
  );
}