"""连续性追踪 API Schema。"""
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WriteConstraints(BaseModel):
    """本章约束锁：项目事实优先于任何写作技法。"""

    model_config = ConfigDict(extra="ignore")

    word_count_min: int | None = Field(None, ge=100, le=20_000)
    word_count_max: int | None = Field(None, ge=100, le=20_000)
    must_happen: list[str] = Field(default_factory=list, max_length=20)
    must_not_happen: list[str] = Field(default_factory=list, max_length=20)
    time_anchor: str = Field(default="", max_length=200)
    stop_point: str = Field(default="", max_length=200)
    end_hook_debt: str = Field(default="", max_length=500)

    @field_validator("word_count_min", "word_count_max", mode="before")
    @classmethod
    def _empty_word_count(cls, value):
        """LLM 常给 0 / 空串，按未填写处理。"""
        if value in (None, "", 0, "0", "null", "None"):
            return None
        return value

    @field_validator("must_happen", "must_not_happen", mode="before")
    @classmethod
    def _coerce_constraint_list(cls, value):
        """兼容把必须/禁止写成一段中文。"""
        if value is None or value == "":
            return []
        if isinstance(value, str):
            return [p.strip() for p in value.replace("；", "\n").split("\n") if p.strip()]
        if isinstance(value, list):
            out: list[str] = []
            for item in value:
                if isinstance(item, str) and item.strip():
                    out.append(item.strip())
                elif isinstance(item, dict):
                    text = str(item.get("title") or item.get("text") or "").strip()
                    if text:
                        out.append(text)
            return out
        return []

    @field_validator("time_anchor", "stop_point", mode="before")
    @classmethod
    def _clip_short_text(cls, value):
        """过长锚点截断，避免整份细纲校验失败。"""
        return str(value or "")[:200]

    @field_validator("end_hook_debt", mode="before")
    @classmethod
    def _clip_hook(cls, value):
        """章尾新债截断到 schema 上限。"""
        return str(value or "")[:500]


class ForeshadowItem(BaseModel):
    """伏笔账本条目。"""

    id: str
    title: str
    description: str = ""
    status: Literal["open", "paid", "broken"] = "open"
    planted_chapter_id: str | None = None
    payoff_chapter_id: str | None = None
    character_names: list[str] = Field(default_factory=list)


class ForeshadowUpsert(BaseModel):
    """新建或更新伏笔。"""

    id: str | None = None
    title: str = Field(..., min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    status: Literal["open", "paid", "broken"] | None = None
    planted_chapter_id: UUID | None = None
    payoff_chapter_id: UUID | None = None
    character_names: list[str] = Field(default_factory=list, max_length=20)


class CharacterRuntimeState(BaseModel):
    """角色运行时状态（不是人设卡）。"""

    character_id: str
    name: str = ""
    location: str = ""
    goal: str = ""
    known_facts: list[str] = Field(default_factory=list)
    unknown_facts: list[str] = Field(default_factory=list)
    open_threads: list[str] = Field(default_factory=list)


class CharacterStateUpdate(BaseModel):
    """一章内对角色状态的增量。"""

    character_id: UUID
    name: str | None = None
    location: str | None = None
    goal: str | None = None
    known_facts_add: list[str] = Field(default_factory=list, max_length=20)
    unknown_facts_add: list[str] = Field(default_factory=list, max_length=20)
    known_facts: list[str] | None = Field(None, max_length=40)
    unknown_facts: list[str] | None = Field(None, max_length=40)
    open_threads: list[str] | None = None


class TimelineEvent(BaseModel):
    """作者真相或读者已知上的一条事件。"""

    text: str
    chapter_id: str | None = None


class ChapterTrackRecord(BaseModel):
    """单章连续性增量。"""

    chapter_id: str | None = None
    note: str = ""


class TrackingCommitRequest(BaseModel):
    """写完一章后提交增量；禁止手改派生摘要。"""

    chapter_id: UUID | None = None
    foreshadows_planted: list[ForeshadowUpsert] = Field(default_factory=list, max_length=20)
    foreshadows_paid: list[str] = Field(default_factory=list, max_length=50)
    character_updates: list[CharacterStateUpdate] = Field(default_factory=list, max_length=30)
    author_events: list[str] = Field(default_factory=list, max_length=20)
    reader_events: list[str] = Field(default_factory=list, max_length=20)
    note: str = Field(default="", max_length=3072)


class WriterContextCard(BaseModel):
    """Writer 写前加载的短上下文卡。"""

    constraints: WriteConstraints
    character_states: list[CharacterRuntimeState] = Field(default_factory=list)
    open_foreshadows: list[ForeshadowItem] = Field(default_factory=list)
    author_timeline: list[TimelineEvent] = Field(default_factory=list)
    reader_timeline: list[TimelineEvent] = Field(default_factory=list)
    last_chapter_id: str | None = None


class TrackingStateRead(BaseModel):
    """作品追踪总览（派生视图，可给 UI，不进正文 prompt 全文）。"""

    model_config = ConfigDict(from_attributes=True)

    work_id: UUID
    revision: int
    last_chapter_id: str | None = None
    foreshadows: list[ForeshadowItem] = Field(default_factory=list)
    character_states: list[CharacterRuntimeState] = Field(default_factory=list)
    author_timeline: list[TimelineEvent] = Field(default_factory=list)
    reader_timeline: list[TimelineEvent] = Field(default_factory=list)
    chapter_records: list[ChapterTrackRecord] = Field(default_factory=list)
    context_card: WriterContextCard | None = None
