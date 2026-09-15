import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { App, Button, Input, Space, Spin, InputNumber, Checkbox, Empty } from 'antd';
import {
  X,
  BookOpen,
  Building2,
  Rocket,
  Building,
  Brain,
  Heart,
  Sword,
  Plus,
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
  Circle,
  Hash,
  Flag,
  Sparkles,
  GripVertical,
  Trash2,
  Info,
} from 'lucide-react';

import { worksApi, outlineApi, type Genre, type PlotVolume } from '@/api';
import { useCurrentWorkStore } from '@/stores/useCurrentWorkStore';

const STEPS = [
  { key: 'basics', label: '基础信息' },
  { key: 'genre',  label: '体裁与受众' },
  { key: 'world',  label: '世界观种子' },
  { key: 'outline', label: 'AI 推荐大纲' },
  { key: 'review', label: '确认创建' },
];

/** 向后端 Genre 枚举映射 —— 'wuxia' 与 'custom' 折叠到相近的官方分类 */
const GENRE_TO_BACKEND: Record<string, Genre> = {
  fantasy:    'fantasy',
  urban:      'urban',
  sci_fi:     'sci_fi',
  historical: 'historical',
  mystery:    'mystery',
  romance:    'romance',
  wuxia:      'fantasy',   // 武侠归入玄幻
  custom:     'other',
};

const GENRES = [
  { key: 'fantasy',    label: '玄幻 / 修仙', desc: '修炼体系 + 异世界',  Icon: BookOpen,       checked: true },
  { key: 'urban',      label: '都市 / 现实', desc: '现代背景 + 情感',    Icon: Building2,      checked: false },
  { key: 'sci_fi',     label: '科幻 / 末世', desc: '技术设定 + 推演',    Icon: Rocket,         checked: true },
  { key: 'historical', label: '历史 / 架空', desc: '朝代 / 异世界历史',  Icon: Building,      checked: false },
  { key: 'mystery',    label: '悬疑 / 推理', desc: '案件 + 反转',         Icon: Brain,          checked: false },
  { key: 'romance',    label: '言情 / 甜宠', desc: '情感主线',            Icon: Heart,          checked: false },
  { key: 'wuxia',      label: '武侠 / 仙侠', desc: '江湖 / 门派',         Icon: Sword,          checked: false },
  { key: 'custom',     label: '自定义',       desc: '告诉我更多…',        Icon: Plus,           checked: false },
];

const SELECTED_KEYWORDS = ['热血狂飙', '杀伐果断', '严谨设定', '反转不断'];
const CANDIDATE_KEYWORDS = ['轻松幽默', '智商在线', '群像推演', '慢热种田', '甜虐交织', '史诗气魄'];

/** 将"100 万字" / "80万字" / "500000" 解析为整数，非法时返回 fallback */
function parseWordCount(input: string, fallback = 1_000_000): number {
  const m = input.match(/([\d.]+)/);
  if (!m) return fallback;
  const num = parseFloat(m[1]);
  if (!Number.isFinite(num) || num <= 0) return fallback;
  if (/万/.test(input)) return Math.round(num * 10_000);
  return Math.round(num);
}

export default function NewWorkWizardPage() {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const setCurrentWorkId = useCurrentWorkStore((s) => s.setCurrentWorkId);

  const [step, setStep] = useState(0); // 0-based: 0..4
  const [audience, setAudience] = useState<'male' | 'female' | 'all'>('male');
  const [pace, setPace] = useState<'slow' | 'balanced' | 'fast'>('balanced');
  const [genre, setGenre] = useState<Set<string>>(
    new Set(GENRES.filter((g) => g.checked).map((g) => g.key))
  );
  const [keywords, setKeywords] = useState<Set<string>>(new Set(SELECTED_KEYWORDS));

  // Step 1 字段
  const [title, setTitle] = useState('剑来·前传');
  const [logline, setLogline] = useState('讲述陈平安从骊珠洞天走出后的一段尘缘。');
  const [penName, setPenName] = useState('烽火戏诸侯');
  const [volume1Name, setVolume1Name] = useState('少年游');

  // Step 2 字段
  const [chapterWords, setChapterWords] = useState('3,500');
  const [targetTotal, setTargetTotal] = useState('100 万字');

  // Step 4 (AI 大纲) 状态
  const [aiVolumes, setAiVolumes] = useState<PlotVolume[]>([]);
  const [aiChecked, setAiChecked] = useState<Set<number>>(new Set()); // vol_no 集合
  const [aiTotalVolumes, setAiTotalVolumes] = useState(3);
  const [aiTargetChapters, setAiTargetChapters] = useState<number | null>(null);
  const [aiHint, setAiHint] = useState('');

  const [submitting, setSubmitting] = useState(false);

  const toggleGenre = (key: string) => {
    setGenre((prev) => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  };
  const toggleKeyword = (k: string) => {
    setKeywords((prev) => {
      const next = new Set(prev);
      next.has(k) ? next.delete(k) : next.add(k);
      return next;
    });
  };

  // 派生数据
  const primaryGenre = useMemo<Genre>(() => {
    const first = [...genre][0];
    return (first && GENRE_TO_BACKEND[first]) || 'other';
  }, [genre]);

  const audienceArr = useMemo(() => {
    if (audience === 'male') return ['男频'];
    if (audience === 'female') return ['女频'];
    return ['不限'];
  }, [audience]);

  const targetWordCount = useMemo(() => parseWordCount(targetTotal, 1_000_000), [targetTotal]);

  // AI 大纲预览
  const aiPreviewMutation = useMutation({
    mutationFn: () =>
      outlineApi.aiPreview({
        work_preview: {
          title: title.trim(),
          genre: primaryGenre,
          logline: logline.trim(),
          style_keywords: [...keywords],
          target_audience: audienceArr,
          target_word_count: targetWordCount,
        },
        total_volumes: aiTotalVolumes,
        target_chapter_count: aiTargetChapters,
        extra_hint: aiHint.trim() || undefined,
      }),
    onSuccess: (resp) => {
      if (!resp.volumes.length) {
        message.warning('AI 未能生成有效大纲（输出格式异常），请重试');
        return;
      }
      setAiVolumes(resp.volumes);
      setAiChecked(new Set(resp.volumes.map((v) => v.vol_no)));
      message.success(`已生成 ${resp.volumes.length} 卷大纲`);
    },
    onError: (err: unknown) => {
      message.error(err instanceof Error ? err.message : 'AI 推荐失败');
    },
  });

  const toggleAiVolume = (volNo: number) => {
    setAiChecked((prev) => {
      const next = new Set(prev);
      next.has(volNo) ? next.delete(volNo) : next.add(volNo);
      return next;
    });
  };

  const selectedVolumes = useMemo(
    () => aiVolumes.filter((v) => aiChecked.has(v.vol_no)),
    [aiVolumes, aiChecked],
  );

  const aiOutlineCount = useMemo(
    () => selectedVolumes.reduce((sum, v) => sum + v.chapters.length, 0),
    [selectedVolumes],
  );

  /** 真正调用后端 API 创建作品 + 写入大纲 */
  const handleCreate = async () => {
    if (!title.trim()) {
      message.warning('请填写作品标题');
      setStep(0);
      return;
    }
    setSubmitting(true);
    try {
      const created = await worksApi.create({
        title: title.trim(),
        genre: primaryGenre,
        logline: logline.trim(),
        target_word_count: targetWordCount,
        style_keywords: [...keywords],
        target_audience: audienceArr,
      });
      // 若用户在第 4 步勾选了 AI 大纲,落库
      if (selectedVolumes.length > 0) {
        try {
          await outlineApi.bulkCreate(created.id, { volumes: selectedVolumes });
          message.success(`作品 + ${selectedVolumes.length} 卷大纲已创建`);
        } catch (err) {
          const msg = err instanceof Error ? err.message : '大纲写入失败';
          message.warning(`作品已创建,但大纲写入失败: ${msg}`);
        }
      } else {
        message.success(`作品《${created.title}》创建成功`);
      }
      navigate(`/works/${created.id}/outline`);
      setCurrentWorkId(created.id);
    } catch (err) {
      const msg = err instanceof Error ? err.message : '创建失败';
      message.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const next = () => setStep((s) => Math.min(STEPS.length - 1, s + 1));
  const prev = () => setStep((s) => Math.max(0, s - 1));

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40 backdrop-blur-sm overflow-auto p-6">
      {/* Modal */}
      <div className="bg-surface-container-lowest rounded-2xl shadow-L3-modal w-full max-w-[1120px] max-h-[920px] overflow-hidden flex flex-col my-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-8 py-4 border-b border-outline-variant/30">
          <div className="flex flex-col gap-1">
            <h2 className="text-headline-md font-bold text-on-surface">
              新建作品向导
            </h2>
            <p className="text-body-sm text-on-surface-variant">
              第 {step + 1} 步 / 共 {STEPS.length} 步 · {STEPS[step].label}
            </p>
          </div>
          <Button
            type="text"
            shape="circle"
            icon={<X size={24} />}
            onClick={() => navigate('/works')}
            disabled={submitting}
            aria-label="关闭向导"
          />
        </div>

        {/* Stepper */}
        <div className="flex items-center gap-3 px-8 py-3 bg-surface-container-low border-b border-outline-variant/30 overflow-x-auto">
          {STEPS.map((s, i) => {
            const done = i < step;
            const active = i === step;
            return (
              <div key={s.key} className="flex items-center gap-3 flex-1 last:flex-initial">
                <div className="flex items-center gap-2">
                  <span
                    className={`w-7 h-7 rounded-full flex items-center justify-center text-label-md font-semibold ${
                      done
                        ? 'bg-primary text-white'
                        : active
                          ? 'bg-primary text-white'
                          : 'bg-surface-container text-on-surface-variant'
                    }`}
                  >
                    {done ? <CheckCircle2 size={16} /> : i + 1}
                  </span>
                  <span
                    className={`text-label-md whitespace-nowrap ${
                      active ? 'text-on-surface font-semibold' : 'text-on-surface-variant'
                    }`}
                  >
                    {s.label}
                  </span>
                </div>
                {i < STEPS.length - 1 && (
                  <div className={`flex-1 h-px ${done || active ? 'bg-primary' : 'bg-outline-variant'}`} />
                )}
              </div>
            );
          })}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-8 py-6 flex flex-col gap-6">
          {step === 0 && (
            <StepBasics
              title={title}
              logline={logline}
              penName={penName}
              volume1Name={volume1Name}
              onTitle={setTitle}
              onLogline={setLogline}
              onPenName={setPenName}
              onVolume1Name={setVolume1Name}
            />
          )}
          {step === 1 && (
            <>
              <div className="flex flex-col gap-3">
                <h3 className="text-headline-sm font-semibold text-on-surface">
                  选择体裁 <span className="text-body-sm text-on-surface-variant font-normal">（可多选 1-3 个）</span>
                </h3>
                <div className="grid grid-cols-4 gap-4">
                  {GENRES.map((g) => {
                    const checked = genre.has(g.key);
                    return (
                      <Button
                        key={g.key}
                        type="default"
                        onClick={() => toggleGenre(g.key)}
                        className={`!h-auto !p-4 !rounded-xl !text-left !border-2 ${
                          checked
                            ? '!border-primary !bg-primary-container'
                            : '!border-outline-variant/40 !bg-surface-container-lowest hover:!border-primary-container'
                        }`}
                        style={{ display: 'flex', flexDirection: 'column', gap: 8 }}
                      >
                        <div className="flex items-center justify-between w-full">
                          <g.Icon
                            size={28}
                            className={checked ? 'text-primary' : 'text-outline'}
                          />
                          {checked ? (
                            <CheckCircle2 size={20} className="text-primary" />
                          ) : (
                            <Circle size={20} className="text-outline" />
                          )}
                        </div>
                        <span className="text-label-lg font-semibold text-on-surface">
                          {g.label}
                        </span>
                        <span className="text-body-sm text-on-surface-variant">{g.desc}</span>
                      </Button>
                    );
                  })}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-6">
                <div className="flex flex-col gap-3">
                  <h3 className="text-headline-sm font-semibold text-on-surface">受众定位</h3>
                  <Space.Compact className="!w-full">
                    {(['male', 'female', 'all'] as const).map((k) => (
                      <Button
                        key={k}
                        type={audience === k ? 'primary' : 'default'}
                        ghost={audience === k}
                        block
                        onClick={() => setAudience(k)}
                      >
                        {k === 'male' ? '男频' : k === 'female' ? '女频' : '不限'}
                      </Button>
                    ))}
                  </Space.Compact>
                  <div className="flex flex-col gap-2 mt-2">
                    <label className="text-label-md text-on-surface">读者画像</label>
                    <Input.TextArea
                      rows={4}
                      defaultValue="15-35 岁男性读者，热衷爽文节奏与修炼升级，期待清晰的目标—冲突—收获循环。"
                    />
                  </div>
                </div>

                <div className="flex flex-col gap-3">
                  <h3 className="text-headline-sm font-semibold text-on-surface">节奏与字数</h3>
                  <div className="flex flex-col gap-1">
                    <label className="text-label-sm text-on-surface-variant">章节目标字数</label>
                    <Input
                      prefix={<Hash size={18} className="text-outline" />}
                      value={chapterWords}
                      onChange={(e) => setChapterWords(e.target.value)}
                      className="!font-code-md"
                    />
                  </div>
                  <div className="flex flex-col gap-1">
                    <label className="text-label-sm text-on-surface-variant">作品目标总字数</label>
                    <Input
                      prefix={<Flag size={18} className="text-outline" />}
                      value={targetTotal}
                      onChange={(e) => setTargetTotal(e.target.value)}
                      className="!font-code-md"
                    />
                  </div>
                  <div className="mt-2">
                    <Space.Compact className="!w-full">
                      {(['slow', 'balanced', 'fast'] as const).map((p) => (
                        <Button
                          key={p}
                          type={pace === p ? 'primary' : 'default'}
                          ghost={pace === p}
                          block
                          onClick={() => setPace(p)}
                        >
                          {p === 'slow' ? '慢热' : p === 'balanced' ? '均衡' : '快节奏'}
                        </Button>
                      ))}
                    </Space.Compact>
                  </div>
                </div>
              </div>

              <div className="flex flex-col gap-2">
                <h3 className="text-headline-sm font-semibold text-on-surface">
                  风格关键词 <span className="text-body-sm text-on-surface-variant font-normal">（最多 8 个）</span>
                </h3>
                <div className="flex flex-wrap gap-1.5">
                  {[...keywords].map((k) => (
                    <Button
                      key={k}
                      type="primary"
                      shape="round"
                      icon={<X size={14} />}
                      iconPosition="end"
                      onClick={() => toggleKeyword(k)}
                      style={{ background: 'var(--ant-color-primary-container, #ccfbf1)', color: 'var(--ant-color-on-primary-container, #134e4a)' }}
                    >
                      {k}
                    </Button>
                  ))}
                  {CANDIDATE_KEYWORDS.filter((k) => !keywords.has(k)).map((k) => (
                    <Button
                      key={k}
                      type="default"
                      shape="round"
                      onClick={() => toggleKeyword(k)}
                    >
                      {k}
                    </Button>
                  ))}
                </div>
              </div>
            </>
          )}
          {step === 2 && (
            <StepWorld
              protagonist="陈平安"
              onProtagonist={() => {/* kept static */}}
            />
          )}
          {step === 3 && (
            <StepAiOutline
              totalVolumes={aiTotalVolumes}
              onTotalVolumes={setAiTotalVolumes}
              targetChapters={aiTargetChapters}
              onTargetChapters={setAiTargetChapters}
              hint={aiHint}
              onHint={setAiHint}
              volumes={aiVolumes}
              checked={aiChecked}
              onToggle={toggleAiVolume}
              loading={aiPreviewMutation.isPending}
              onGenerate={() => aiPreviewMutation.mutate()}
              error={aiPreviewMutation.error ? (aiPreviewMutation.error as Error).message : null}
            />
          )}
          {step === 4 && (
            <StepReview
              title={title}
              logline={logline}
              penName={penName}
              volume1Name={volume1Name}
              genre={[...genre].map((k) => GENRES.find((g) => g.key === k)?.label ?? k)}
              audience={audienceArr.join(' · ')}
              pace={pace === 'slow' ? '慢热' : pace === 'balanced' ? '均衡' : '快节奏'}
              chapterWords={chapterWords}
              targetTotal={targetTotal}
              keywords={[...keywords]}
              aiOutlineCount={aiOutlineCount}
              aiVolumeCount={selectedVolumes.length}
            />
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-8 py-4 border-t border-outline-variant/30 bg-surface-container-low">
          <div className="flex items-center gap-2">
            <Sparkles size={18} className="text-tertiary" />
            <span className="text-body-sm text-on-surface-variant">
              {step < 2
                ? '下一步补世界观与受众；创建后停在细纲，不会自动写正文'
                : step === 3
                  ? '勾选的大纲会在创建时写入；不会调用 Writer 写第 1 章'
                  : '创建后进入大纲页。点「写第 1 章」才会进编辑器'}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <Button
              type="default"
              icon={<ArrowLeft size={16} />}
              disabled={step === 0 || submitting}
              onClick={prev}
            >
              上一步
            </Button>
            {step < STEPS.length - 1 ? (
              <Button
                type="primary"
                icon={<ArrowRight size={18} />}
                iconPosition="end"
                onClick={next}
                disabled={submitting}
              >
                下一步
              </Button>
            ) : (
              <Button
                type="primary"
                icon={<ArrowRight size={18} />}
                iconPosition="end"
                onClick={handleCreate}
                disabled={submitting}
                loading={submitting}
              >
                {submitting ? '创建中…' : '创建作品'}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

interface StepBasicsProps {
  title: string;
  logline: string;
  penName: string;
  volume1Name: string;
  onTitle: (v: string) => void;
  onLogline: (v: string) => void;
  onPenName: (v: string) => void;
  onVolume1Name: (v: string) => void;
}

function StepBasics({
  title, logline, penName, volume1Name,
  onTitle, onLogline, onPenName, onVolume1Name,
}: StepBasicsProps) {
  return (
    <div className="flex flex-col gap-6 max-w-2xl">
      <h3 className="text-headline-sm font-semibold text-on-surface">基础信息</h3>
      <div className="flex flex-col gap-2">
        <label className="text-label-md text-on-surface">作品标题</label>
        <Input
          size="large"
          value={title}
          onChange={(e) => onTitle(e.target.value)}
        />
      </div>
      <div className="flex flex-col gap-2">
        <label className="text-label-md text-on-surface">一句话简介 (Logline)</label>
        <Input.TextArea
          rows={4}
          value={logline}
          onChange={(e) => onLogline(e.target.value)}
        />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="flex flex-col gap-2">
          <label className="text-label-md text-on-surface">主笔名</label>
          <Input
            size="large"
            value={penName}
            onChange={(e) => onPenName(e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-2">
          <label className="text-label-md text-on-surface">第一卷名</label>
          <Input
            size="large"
            value={volume1Name}
            onChange={(e) => onVolume1Name(e.target.value)}
          />
        </div>
      </div>
    </div>
  );
}

interface StepWorldProps {
  protagonist: string;
  onProtagonist: (v: string) => void;
}

function StepWorld({ protagonist: _protagonist, onProtagonist: _onProtagonist }: StepWorldProps) {
  return (
    <div className="flex flex-col gap-4 max-w-3xl">
      <h3 className="text-headline-sm font-semibold text-on-surface">世界观种子（可后续精修）</h3>
      <div className="flex flex-col gap-2">
        <label className="text-label-md text-on-surface">核心矛盾</label>
        <Input.TextArea
          rows={4}
          defaultValue="陈平安要在仙凡混杂的乱世中寻找自己的道，同时守护他珍视的人。"
        />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="flex flex-col gap-2">
          <label className="text-label-md text-on-surface">主角名</label>
          <Input size="large" defaultValue="陈平安" />
        </div>
        <div className="flex flex-col gap-2">
          <label className="text-label-md text-on-surface">起点设定</label>
          <Input size="large" defaultValue="骊珠洞天 · 少年游" />
        </div>
      </div>
      <div className="flex flex-col gap-2">
        <label className="text-label-md text-on-surface">期望前三章的节拍</label>
        <div className="flex flex-col gap-2">
          {['楔子：骊珠洞天少年不识愁滋味', '第一章：邻居少年远行求学', '第二章：入山门拜师'].map((b, i) => (
            <div key={i} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-surface-container-low border border-outline-variant/40">
              <GripVertical size={18} className="text-primary" />
              <span className="font-code-sm text-on-surface-variant w-6">{i + 1}</span>
              <span className="flex-1 text-body-md text-on-surface">{b}</span>
              <Button type="text" shape="circle" danger icon={<Trash2 size={18} />} aria-label="删除节拍" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

interface StepAiOutlineProps {
  totalVolumes: number;
  onTotalVolumes: (v: number) => void;
  targetChapters: number | null;
  onTargetChapters: (v: number | null) => void;
  hint: string;
  onHint: (v: string) => void;
  volumes: PlotVolume[];
  checked: Set<number>;
  onToggle: (volNo: number) => void;
  loading: boolean;
  onGenerate: () => void;
  error: string | null;
}

function StepAiOutline({
  totalVolumes, onTotalVolumes,
  targetChapters, onTargetChapters,
  hint, onHint,
  volumes, checked, onToggle,
  loading, onGenerate, error,
}: StepAiOutlineProps) {
  return (
    <div className="flex flex-col gap-6 max-w-4xl">
      <div>
        <h3 className="text-headline-sm font-semibold text-on-surface flex items-center gap-2">
          <Sparkles size={20} className="text-primary" />
          AI 推荐大纲 <span className="text-body-sm text-on-surface-variant font-normal">（可选,创建作品时一并写入）</span>
        </h3>
        <p className="text-body-sm text-on-surface-variant mt-1">
          根据已填写的体裁 / 简介 / 关键词,让 AI 设计 N 卷大纲;勾选需要的卷,创建时批量写入数据库。
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 surface-card p-4">
        <div className="flex flex-col gap-1">
          <label className="text-label-md text-on-surface">总卷数</label>
          <InputNumber
            min={1}
            max={10}
            value={totalVolumes}
            onChange={(v) => onTotalVolumes(typeof v === 'number' ? v : 3)}
            className="!w-full"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-label-md text-on-surface">目标总章节数 <span className="text-body-xs text-on-surface-variant">（留空自动推算）</span></label>
          <InputNumber
            min={1}
            max={200}
            value={targetChapters ?? undefined}
            onChange={(v) => onTargetChapters(typeof v === 'number' ? v : null)}
            placeholder="自动按字数推算"
            className="!w-full"
          />
        </div>
        <div className="col-span-2 flex flex-col gap-1">
          <label className="text-label-md text-on-surface">附加要求（可选）</label>
          <Input.TextArea
            rows={2}
            maxLength={500}
            showCount
            value={hint}
            onChange={(e) => onHint(e.target.value)}
            placeholder="例:前 3 卷聚焦主角成长,第 4 卷反派登场"
          />
        </div>
        <div className="col-span-2 flex justify-end">
          <Button
            type="primary"
            icon={<Sparkles size={16} />}
            loading={loading}
            onClick={onGenerate}
          >
            {volumes.length ? '重新生成' : '生成 AI 大纲'}
          </Button>
        </div>
        {error && <div className="col-span-2 text-body-sm text-error">生成失败:{error}</div>}
      </div>

      <Spin spinning={loading} tip="AI 正在设计大纲...">
        {volumes.length === 0 ? (
          <Empty description={loading ? '' : '尚未生成;点击「生成 AI 大纲」开始'} />
        ) : (
          <div className="flex flex-col gap-3">
            <div className="text-body-sm text-on-surface-variant">
              已生成 {volumes.length} 卷 / {volumes.reduce((s, v) => s + v.chapters.length, 0)} 章,勾选要采纳的卷。
            </div>
            {volumes.map((v) => (
              <div
                key={v.vol_no}
                className={`surface-card p-4 flex flex-col gap-2 ${checked.has(v.vol_no) ? 'ring-2 ring-primary' : ''}`}
              >
                <div className="flex items-center gap-2">
                  <Checkbox
                    checked={checked.has(v.vol_no)}
                    onChange={() => onToggle(v.vol_no)}
                  >
                    <span className="font-semibold text-on-surface">{v.vol_title}</span>
                    <span className="ml-2 text-body-xs text-on-surface-variant">第 {v.vol_no} 卷 · {v.chapters.length} 章</span>
                  </Checkbox>
                </div>
                {v.summary && <div className="text-body-sm text-on-surface-variant">{v.summary}</div>}
                <div className="flex flex-col gap-1 pl-7">
                  {v.chapters.slice(0, 5).map((c, i) => (
                    <div key={i} className="text-body-sm text-on-surface-variant flex items-start gap-2">
                      <span className="text-outline">·</span>
                      <div className="flex-1">
                        <span className="font-code-sm text-on-surface">{c.title}</span>
                        {c.summary && <span className="ml-2">{c.summary}</span>}
                      </div>
                    </div>
                  ))}
                  {v.chapters.length > 5 && (
                    <div className="text-body-xs text-on-surface-variant">… 等共 {v.chapters.length} 章</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Spin>
    </div>
  );
}

interface StepReviewProps {
  title: string;
  logline: string;
  penName: string;
  volume1Name: string;
  genre: string[];
  audience: string;
  pace: string;
  chapterWords: string;
  targetTotal: string;
  keywords: string[];
  aiVolumeCount: number;
  aiOutlineCount: number;
}

function StepReview({
  title, logline, penName, volume1Name,
  genre, audience, pace, chapterWords, targetTotal, keywords,
  aiVolumeCount, aiOutlineCount,
}: StepReviewProps) {
  return (
    <div className="flex flex-col gap-6 max-w-2xl">
      <div className="surface-card p-6 flex flex-col gap-3">
        <h3 className="text-headline-sm font-semibold text-on-surface pb-2 border-b border-outline-variant/40">
          即将创建
        </h3>
        <Row label="标题" value={title || '（未填）'} />
        <Row label="体裁" value={genre.join(', ') || '（未选）'} />
        <Row label="受众" value={audience} />
        <Row label="节奏" value={pace} />
        <Row label="章节字数" value={chapterWords} />
        <Row label="目标总字数" value={targetTotal} />
        <Row label="风格关键词" value={keywords.join(', ') || '（未选）'} />
        <Row label="主笔名" value={penName} />
        <Row label="第一卷名" value={volume1Name} />
        <Row label="一句话简介" value={logline || '（未填）'} />
        <Row
          label="AI 大纲"
          value={aiVolumeCount > 0 ? `${aiVolumeCount} 卷 / ${aiOutlineCount} 章` : '（跳过,稍后手动创建）'}
          highlight={aiVolumeCount > 0}
        />
      </div>
      <div className="px-3 py-2 rounded-lg bg-tertiary-container/20 text-body-sm text-on-surface-variant">
        <Info size={18} className="align-middle text-tertiary inline" />{' '}
        创建后停在细纲，不会自动写正文。作品库位于{' '}
        <code>data/works/&lt;work_id&gt;/</code>。
      </div>
    </div>
  );
}

function Row({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="flex items-center gap-4">
      <span className="text-label-md text-on-surface-variant w-24">{label}</span>
      <span
        className={`font-code-md break-all ${highlight ? 'text-primary font-semibold' : 'text-on-surface'}`}
      >
        {value}
      </span>
    </div>
  );
}
