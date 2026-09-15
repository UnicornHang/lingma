"""Chapter 相关的 Pydantic Schema"""
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChapterBase(BaseModel):
    """章节基础字段"""

    title: str = Field(..., min_length=1, max_length=200, description="章节标题")
    content: dict[str, Any] = Field(default_factory=dict, description="TipTap JSON")
    plain_content: str = Field(default="", description="纯文本内容")
    summary: str = Field(default="", description="章节摘要")
    key_events: list[str] = Field(default_factory=list, description="关键事件")
    outline_node_id: UUID | None = Field(None, description="关联大纲节点")


class ChapterCreate(ChapterBase):
    """创建章节"""

    work_id: UUID = Field(..., description="所属作品 ID")


class ChapterUpdate(BaseModel):
    """更新章节"""

    title: str | None = Field(None, min_length=1, max_length=200)
    content: dict[str, Any] | None = None
    plain_content: str | None = None
    summary: str | None = None
    key_events: list[str] | None = None
    status: str | None = Field(None, description="draft | generated | reviewed | finalized")


class ChapterRead(ChapterBase):
    """读取章节"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    work_id: UUID
    status: str
    word_count: int
    version: int
    created_at: datetime
    updated_at: datetime


class ChapterListResponse(BaseModel):
    """分页章节列表"""

    total: int
    page: int
    page_size: int
    items: list[ChapterRead]


class GenerateChapterRequest(BaseModel):
    """生成章节请求"""

    chapter_id: UUID | None = Field(None, description="已存在章节 ID（重生成）")
    title: str | None = Field(None, description="新章节标题")
    outline_node_id: UUID | None = Field(None, description="基于哪个大纲节点生成")
    target_word_count: int | None = Field(None, ge=500, le=20_000)
    style_overrides: dict[str, Any] = Field(
        default_factory=dict, description="本次覆盖的 Prompt 变量"
    )
    mode: Literal["continue", "generate"] = Field(
        "continue",
        description="continue=续写已有正文（追加），generate=全量重写整章",
    )
    continue_from_chars: int = Field(
        1500,
        ge=100,
        le=5000,
        description="续写模式下，取章节末尾最近 N 字作为 prompt 上下文",
    )
    # [提交 C] 自动去味开关:生成完成后跑 AI 痕迹检测,blocking 超阈值自动重写一次
    auto_polish: bool = Field(
        True,
        description="生成完成后是否自动跑确定性 AI 痕迹检测(默认开,不自动改写)",
    )
    auto_rewrite: bool = Field(
        False,
        description="检测出阻断级痕迹后是否自动调用模型润色;默认关,不承诺过检测器",
    )
    max_blocking_for_rewrite: int = Field(
        0,
        ge=0,
        le=20,
        description="blocking finding 阈值,达到/超过即触发自动重写;默认 0 即单条就触发",
    )
    # [P2] 自动 critic 评审开关:生成完成后跑 CriticAgent 评分并落库
    auto_critic: bool = Field(
        True,
        description="生成完成后是否自动跑 CriticAgent 多 Persona 评审(默认开)",
    )
    # [P3.3] Critic 触发自动改写:overall < threshold 时整章改写一次再评
    critic_rewrite_threshold: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description=(
            "critic overall 阈值,低于此触发自动改写 + 再评;None 时用 settings "
            "(默认 0.6)。范围 [0.0, 1.0]"
        ),
    )
    critic_rewrite_max: int | None = Field(
        None,
        ge=0,
        le=3,
        description=(
            "单次生成最多改写次数;None 时用 settings (默认 1)。0 = 禁用,"
            "1 = 不达标改一次,2-3 = 多轮迭代"
        ),
    )


class GenerationStreamEvent(BaseModel):
    """生成流式事件"""

    type: str = Field(..., description="事件类型: start | delta | progress | done | error")
    task_id: UUID | None = None
    chapter_id: UUID | None = None
    content: str | None = None
    progress: float | None = None
    error: str | None = None
    metadata: dict[str, Any] | None = None


# ==================== Chapter Version（版本历史）====================


class ChapterVersionRead(BaseModel):
    """章节版本（历史快照，只读）"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chapter_id: UUID
    version_no: int
    plain_content: str = ""
    generated_by: str = ""
    prompt_used: str = ""
    model_used: str = ""
    token_usage: dict[str, Any] = Field(default_factory=dict)
    note: str = ""
    created_at: datetime


class ChapterVersionListResponse(BaseModel):
    """章节版本列表"""

    total: int
    items: list[ChapterVersionRead]


# ==================== Editor Agent: AI 痕迹检测与去味 ====================


class PatternFindingRead(BaseModel):
    """单条 AI 痕迹命中"""

    category: str = Field(..., description="类别短码(neg-pos-flip, trailer-summary …)")
    severity: str = Field(..., description="blocking | advisory")
    start: int = Field(..., description="起始字符偏移(半开区间)")
    end: int = Field(..., description="结束字符偏移")
    snippet: str = Field(..., description="触发片段(最多 80 字)")
    message: str = Field(..., description="人话描述")
    rule: str = Field(default="", description="触发的具体规则")


class AnalyzeChapterRequest(BaseModel):
    """AI 痕迹检测请求(纯本地,无 LLM 调用)"""

    text: str = Field(..., min_length=1, description="待检测文本")


class AnalyzeChapterResponse(BaseModel):
    """AI 痕迹检测响应"""

    findings: list[PatternFindingRead]
    blocking_count: int
    advisory_count: int
    stats: dict[str, Any] = Field(default_factory=dict)


class PolishRewriteRead(BaseModel):
    """单条 finding 的改写结果"""

    category: str
    original: str
    rewritten: str
    reason: str


class PolishChapterRequest(BaseModel):
    """章节去味请求(调 LLM)"""

    text: str = Field(..., min_length=1, description="待润色文本")
    style_keywords: list[str] | None = Field(default=None, description="文风关键词锚点")
    temperature: float = Field(default=0.6, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=256, le=20_000)


class PolishChapterResponse(BaseModel):
    """章节去味响应"""

    findings: list[PatternFindingRead]
    rewrites: list[PolishRewriteRead]
    polished_text: str = Field(..., description="应用改写后的全文(若 LLM 失败则等于原文)")
    summary: str
    stats: dict[str, Any] = Field(default_factory=dict)