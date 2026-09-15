"""章节 CRUD API"""
import asyncio
import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.editor_agent import (
    PolishRewrite,
    _extract_json_object,
    get_editor_agent,
)
from app.deps import get_db
from app.prompts.editor_prompts import (
    build_editor_system_prompt,
    build_editor_user_prompt,
)
from app.services import prompt_template_service
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
from app.schemas.critic import CriticEvaluationListItem
from app.services import chapter_service
from app.services import work_service
from app.services.outline_gate import OutlineGateError, resolve_outline_for_write
from app.services.ai_pattern_detector import summarize as summarize_findings
from app.services.llm_service import (
    LLMMessage,
    LLMRequest,
    get_llm_service,
    resolve_provider_config,
)

logger = logging.getLogger(__name__)

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

    outline_id = payload.outline_node_id if payload else None
    try:
        await resolve_outline_for_write(db, chapter, outline_id)
    except OutlineGateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc

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


# ==================== [P3.2] Critic 评分趋势端点 ====================


@router.get(
    "/{chapter_id}/evaluations",
    response_model=list[CriticEvaluationListItem],
    summary="获取章节的 Critic 评审历史(按时间正序)",
    description=(
        "返回该章节的所有 critic_evaluations 记录,按 created_at ASC 排列。"
        "前端用于绘制评分趋势图(echarts)。\n\n"
        "**数据语义**: 每条记录是评审当时的快照,与当前 chapter.version 内容"
        "不一定匹配——前端必须显式 disclaimer。\n\n"
        "**空数据**: 章节无评审记录时返 200 + 空列表(不返 404)。"
    ),
)
async def list_chapter_evaluations_endpoint(
    chapter_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> list[CriticEvaluationListItem]:
    """章节评审历史 —— P3.2 critic 趋势图用。"""
    # 校验章节存在(无评审时仍 200,但章节不存在返 404)
    await chapter_service.get_chapter(db, chapter_id)

    from app.models.critic_evaluation import CriticEvaluation

    r = await db.execute(
        select(CriticEvaluation)
        .where(CriticEvaluation.chapter_id == chapter_id)
        .order_by(CriticEvaluation.created_at.asc())
    )
    rows = list(r.scalars().all())
    return [CriticEvaluationListItem.model_validate(row) for row in rows]


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
        db=db,
    )
    return PolishChapterResponse(
        findings=[PatternFindingRead(**f.to_dict()) for f in result.findings],
        rewrites=[PolishRewriteRead(**r.to_dict()) for r in result.rewrites],
        polished_text=result.polished_text,
        summary=result.summary,
        stats=result.stats,
    )


# ==================== 流式去味 (SSE) ====================
#
# 解决 `/polish` 在长章节 + 推理型 LLM 上 30s+ 必超时的问题。
# 设计:
# 1) 立即 emit `detected` 事件(findings + counts + stats) —— 用户毫秒级看到报告
# 2) emit `llm_started` —— UI 切换到「正在改写」spinner
# 3) emit `llm_delta` 多个 —— LLM 实时输出片段(让连接保活 + 显示进度)
# 4) LLM 流完 → 解析 JSON → 应用 rewrites → emit `done`
# 5) 任一阶段失败 → emit `error`(降级为原文 + findings)
#
# SSE 协议约定:
#   event: <name>\n
#   data: <json>\n\n
# 前端用 fetch + ReadableStream 解析(见 frontend/src/api/chapters.ts)。



def _sse(event: str, payload: dict) -> str:
    """构造单条 SSE 消息。"""
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post(
    "/polish/stream",
    summary="章节去味(SSE 流式,带实时进度)",
    description=(
        "完整去味流程的流式版本。事件序列:detected → llm_started → llm_delta* → done。\n"
        "前端用 EventSource 或 fetch+ReadableStream 接收。\n"
        "对比 `/polish` 的优势:\n"
        "- 检测结果立即返回(避免长章节 30s+ 超时)\n"
        "- 流式 LLM delta 让用户看到进度\n"
        "- LLM 失败时优雅降级返回 findings 报告"
    ),
)
async def polish_chapter_stream_endpoint(
    payload: PolishChapterRequest,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    text = payload.text
    style_keywords = payload.style_keywords
    temperature = payload.temperature
    # 流式版本放宽 max_tokens 上限(原本 4096 容易截断长章节改写)
    max_tokens = max(payload.max_tokens, 8192)

    cfg = await resolve_provider_config(db, agent_type="editor")
    agent = get_editor_agent()

    async def event_gen():
        # ===== 阶段 1:检测(本地,毫秒级) =====
        try:
            findings = agent._detector.detect(text)
        except Exception as e:
            logger.exception("polish stream: 检测阶段失败")
            yield _sse("error", {"phase": "detect", "error": str(e)})
            return

        blocking_count = sum(1 for f in findings if f.severity.value == "blocking")
        advisory_count = sum(1 for f in findings if f.severity.value == "advisory")
        stats = summarize_findings(findings)
        yield _sse("detected", {
            "findings": [f.to_dict() for f in findings],
            "blocking_count": blocking_count,
            "advisory_count": advisory_count,
            "stats": stats,
        })

        # 无 findings → 直接 done,跳过 LLM
        if not findings:
            yield _sse("done", {
                "polished_text": text,
                "rewrites": [],
                "summary": "未检测到 AI 痕迹,无需润色",
                "stats": stats,
            })
            return

        # ===== 阶段 2:流式 LLM 改写 =====
        yield _sse("llm_started", {"model": cfg.model if cfg else "mock"})

        system = await prompt_template_service.resolve_system_prompt(
            db,
            "editor",
            fallback=build_editor_system_prompt(),
        )
        user = build_editor_user_prompt(
            chapter_text=text,
            findings=findings,
            style_keywords=style_keywords,
        )
        req = LLMRequest(
            messages=[
                LLMMessage(role="system", content=system),
                LLMMessage(role="user", content=user),
            ],
            model=cfg.model if cfg else "mock",
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        llm = get_llm_service()
        raw_chunks: list[str] = []
        try:
            async for delta in llm.stream(req, cfg):
                if delta:
                    raw_chunks.append(delta)
                    yield _sse("llm_delta", {"content": delta})
                # 让出事件循环,避免阻塞其它连接
                await asyncio.sleep(0)
        except Exception as e:
            logger.warning("polish stream: LLM 流式失败,降级返回原文(%s)", e)
            yield _sse("error", {
                "phase": "llm",
                "error": str(e),
                "fallback": {
                    "polished_text": text,
                    "rewrites": [],
                    "summary": f"LLM 流式失败({e.__class__.__name__}),已返回原文 + findings 报告",
                    "stats": stats,
                },
            })
            return

        # ===== 阶段 3:解析 LLM 完整输出 =====
        raw = "".join(raw_chunks)
        rewrites: list[PolishRewrite] = []
        summary = "本次未执行 LLM 改写"
        json_text = _extract_json_object(raw)
        if json_text:
            try:
                payload_json = json.loads(json_text)
                rewrites = [
                    PolishRewrite(
                        category=str(r.get("category", "")),
                        original=str(r.get("original", "")),
                        rewritten=str(r.get("rewritten", "")),
                        reason=str(r.get("reason", "")),
                    )
                    for r in payload_json.get("rewrites", [])
                ]
                summary = str(payload_json.get("summary", summary))
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning("polish stream: JSON 解析失败(%s)", e)
                summary = "LLM 输出非 JSON,已返回原文 + findings 报告"
        else:
            logger.warning(
                "polish stream: LLM 输出无法解析为 JSON, raw_len=%d", len(raw),
            )
            summary = "LLM 输出非 JSON,已返回原文 + findings 报告"

        polished = agent._apply_rewrites(text, findings, rewrites)

        yield _sse("done", {
            "polished_text": polished,
            "rewrites": [r.to_dict() for r in rewrites],
            "summary": summary,
            "stats": stats,
        })

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲,确保实时推送
            "Connection": "keep-alive",
        },
    )