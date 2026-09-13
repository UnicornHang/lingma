"""章节 CRUD API"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.editor_agent import get_editor_agent
from app.deps import get_db
from app.models.chapter import ChapterVersion
from app.models.task import GenerationTask, TaskStatus, TaskType
from app.schemas.chapter import (
    AnalyzeChapterRequest,
    AnalyzeChapterResponse,
    ChapterCreate,
    ChapterListResponse,
    ChapterRead,
    ChapterUpdate,
    ChapterVersionListResponse,
    ChapterVersionRead,
    GenerateChapterRequest,
    PatternFindingRead,
    PolishChapterRequest,
    PolishChapterResponse,
    PolishRewriteRead,
)
from app.services import chapter_service
from app.services import work_service
from app.services.llm_service import resolve_provider_config

router = APIRouter()


@router.get(
    "/",
    response_model=ChapterListResponse,
    summary="按作品列出章节",
)
async def list_chapters_endpoint(
    work_id: UUID = Query(..., description="所属作品 ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> ChapterListResponse:
    # 校验作品存在
    await work_service.get_work(db, work_id)
    items, total = await chapter_service.list_chapters(
        db, work_id, page=page, page_size=page_size
    )
    return ChapterListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[ChapterRead.model_validate(it) for it in items],
    )


@router.post(
    "/",
    response_model=ChapterRead,
    status_code=status.HTTP_201_CREATED,
    summary="创建章节",
)
async def create_chapter_endpoint(
    payload: ChapterCreate,
    db: AsyncSession = Depends(get_db),
) -> ChapterRead:
    chapter = await chapter_service.create_chapter(db, payload)
    await db.commit()
    await db.refresh(chapter)
    return ChapterRead.model_validate(chapter)


@router.get(
    "/{chapter_id}",
    response_model=ChapterRead,
    summary="获取章节详情",
)
async def get_chapter_endpoint(
    chapter_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ChapterRead:
    chapter = await chapter_service.get_chapter(db, chapter_id)
    return ChapterRead.model_validate(chapter)


@router.patch(
    "/{chapter_id}",
    response_model=ChapterRead,
    summary="更新章节",
)
async def update_chapter_endpoint(
    chapter_id: UUID,
    payload: ChapterUpdate,
    db: AsyncSession = Depends(get_db),
) -> ChapterRead:
    chapter = await chapter_service.update_chapter(db, chapter_id, payload)
    await db.commit()
    await db.refresh(chapter)
    return ChapterRead.model_validate(chapter)


@router.delete(
    "/{chapter_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除章节",
)
async def delete_chapter_endpoint(
    chapter_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    await chapter_service.delete_chapter(db, chapter_id)
    await db.commit()


@router.post(
    "/{chapter_id}/generate",
    status_code=status.HTTP_202_ACCEPTED,
    summary="异步生成/续写章节",
    description=(
        "创建异步生成任务并返回 task_id 与 WS 地址。"
        "前端需在收到响应后连接 WS：ws://<host>/ws/generation/{task_id}，"
        "发送 {type: 'start', messages: [...], model: '...'} 启动流式输出。"
    ),
)
async def generate_chapter_endpoint(
    chapter_id: UUID,
    payload: GenerateChapterRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    chapter = await chapter_service.get_chapter(db, chapter_id)

    params: dict = {}
    if payload:
        # mode='json' 确保 UUID 等非 JSON 原生类型序列化为字符串,
        # 否则 SQLAlchemy 写 params JSON 列时会抛 TypeError
        params = payload.model_dump(exclude_none=True, mode="json")

    task = GenerationTask(
        work_id=chapter.work_id,
        chapter_id=chapter_id,
        task_type=TaskType.CHAPTER_CONTINUE,
        status=TaskStatus.PENDING,
        params=params,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    return {
        "task_id": str(task.id),
        "ws_url": f"/ws/generation/{task.id}",
        "status": task.status if isinstance(task.status, str) else task.status.value,
        "chapter_id": str(chapter_id),
    }


@router.get(
    "/{chapter_id}/versions",
    response_model=ChapterVersionListResponse,
    summary="章节历史版本列表（按 version_no 倒序）",
)
async def list_chapter_versions_endpoint(
    chapter_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ChapterVersionListResponse:
    """只读,只列出历史版本。不暴露切换/回滚写操作（避免误覆盖当前正文）。"""
    # 校验章节存在
    await chapter_service.get_chapter(db, chapter_id)
    r = await db.execute(
        select(ChapterVersion)
        .where(ChapterVersion.chapter_id == chapter_id)
        .order_by(ChapterVersion.version_no.desc())
    )
    versions = list(r.scalars().all())
    return ChapterVersionListResponse(
        total=len(versions),
        items=[ChapterVersionRead.model_validate(v) for v in versions],
    )


# ==================== Editor Agent: AI 痕迹检测 / 去味 ====================


@router.post(
    "/analyze-ai-patterns",
    response_model=AnalyzeChapterResponse,
    summary="AI 痕迹检测（纯本地，无 LLM 调用）",
    description=(
        "对传入文本跑 AI 痕迹检测器，返回 findings 列表 + 统计。"
        "适用于:写完章节后立即显示报告、用户手动贴入片段检测。"
    ),
)
async def analyze_ai_patterns_endpoint(
    payload: AnalyzeChapterRequest,
) -> AnalyzeChapterResponse:
    agent = get_editor_agent()
    result = agent.analyze(payload.text)
    return AnalyzeChapterResponse(
        findings=[PatternFindingRead(**f) for f in result["findings"]],
        blocking_count=result["blocking_count"],
        advisory_count=result["advisory_count"],
        stats=result["stats"],
    )


@router.post(
    "/polish",
    response_model=PolishChapterResponse,
    summary="章节去味（detect + LLM 改写）",
    description=(
        "完整去味流程:检测 AI 痕迹 → 把 findings + 原文喂给 LLM → 逐条重写 → 返回改写后的全文。"
        "需要配置至少一个可用的 APIConfig(分配给 editor agent),否则降级为仅返回 findings 报告。"
    ),
)
async def polish_chapter_endpoint(
    payload: PolishChapterRequest,
    db: AsyncSession = Depends(get_db),
) -> PolishChapterResponse:
    agent = get_editor_agent()
    cfg = await resolve_provider_config(db, agent_type="editor")
    result = await agent.polish(
        payload.text,
        cfg=cfg,
        style_keywords=payload.style_keywords,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
    )
    return PolishChapterResponse(
        findings=[PatternFindingRead(**f.to_dict()) for f in result.findings],
        rewrites=[PolishRewriteRead(**r.to_dict()) for r in result.rewrites],
        polished_text=result.polished_text,
        summary=result.summary,
        stats=result.stats,
    )