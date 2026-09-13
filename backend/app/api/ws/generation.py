"""WebSocket - 流式生成路由（P2-1：真实 LLM 接入）

协议（前后端约定）：
- 客户端连入
- 服务端发送 {type: "connected", task_id, message}
- 客户端发送 {type: "start"} 触发生成
- 服务端流式返回 {type: "delta", content} ... {type: "done", content, token_usage}
- 服务端可能发送 {type: "error", error}
- 客户端可发送 {type: "ping"} / 服务端回 {type: "pong"}
- 客户端发送 {type: "cancel"} / 服务端回 {type: "cancelled"} 并断开

P2-1 增量：
- 从 DB 拉 GenerationTask 与 chapter 上下文
- 按 task_type 选择对应 Agent（当前仅 writer 实现了真实流）
- 通过 `LLMService.resolve_provider_config` 选 APIConfig
- 读取 task.params 中的 mode/continue_from_chars/target_word_count
  - mode="continue"（默认）：取章节已有正文末尾 N 字作为 existing_tail
  - mode="generate"：全量重写整章
- 流式内容逐 delta 写回 `chapter.plain_content`（带行级节流）
  - continue 模式：plain_content = (已有正文) + (LLM 流式累计)
  - generate 模式：plain_content = LLM 流式累计（覆盖）
- done 时落库：
  - continue 模式：TipTap doc 追加段落（不覆盖原结构）、写入 ChapterVersion(generated_by="ai_revised")、version++、status=generated
  - generate 模式：TipTap doc 单段重置、word_count、version++、status=generated
- 更新 `task.status`、`task.completed_at`、`task.token_usage`（真实用量，非 0）
"""
from __future__ import annotations

import logging
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.agents.writer_agent import WriterAgent
from app.db.session import async_session_factory
from app.models.chapter import Chapter, ChapterStatus, ChapterVersion
from app.models.task import GenerationTask, TaskStatus, TaskType
from app.prompts.editor_prompts import build_rewrite_full_chapter_prompt
from app.services.ai_pattern_detector import AIPatternDetector, Severity, summarize as summarize_findings
from app.services.chapter_role_resolver import resolve_chapter_role
from app.services.chapter_service import count_words
from app.services.llm_service import (
    LLMError,
    LLMMessage,
    LLMRequest,
    ProviderConfig,
    get_llm_service,
    resolve_provider_config,
)

logger = logging.getLogger(__name__)

ws_router = APIRouter()


# ==================== Task → Agent 路由 ====================

AGENT_FOR_TASK: dict[TaskType, str] = {
    TaskType.CHAPTER_CONTINUE: "writer",
    TaskType.CHAPTER_GENERATE: "writer",
    TaskType.CHAPTER_REWRITE: "writer",
    TaskType.CHAPTER_EXPAND: "writer",
    TaskType.CHAPTER_SHORTEN: "writer",
    TaskType.CHAPTER_POLISH: "writer",
}


# ==================== WS 端点 ====================


@ws_router.websocket("/ws/generation/{task_id}")
async def generation_ws(websocket: WebSocket, task_id: str):
    await websocket.accept()
    logger.info("WS 连接建立: task_id=%s", task_id)
    llm = get_llm_service()

    try:
        await websocket.send_json({
            "type": "connected",
            "task_id": task_id,
            "message": "WebSocket 已连接，请发送 start 启动生成",
        })

        while True:
            data = await websocket.receive_json()
            event_type = data.get("type")
            logger.debug("WS 收到: task_id=%s, type=%s", task_id, event_type)

            if event_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif event_type == "start":
                await _handle_start(websocket, task_id, data, llm)

            elif event_type == "cancel":
                await _cancel_task(task_id)
                await websocket.send_json({"type": "cancelled", "task_id": task_id})
                break

            else:
                await websocket.send_json({
                    "type": "error",
                    "error": f"未知事件类型: {event_type}",
                })

    except WebSocketDisconnect:
        logger.info("WS 断开: task_id=%s", task_id)
        await _cancel_task(task_id)
    except Exception as e:
        logger.error("WS 异常: task_id=%s, error=%s", task_id, e, exc_info=True)
        try:
            await websocket.close(code=1011, reason=str(e))
        except Exception:
            pass


# ==================== start 处理 ====================


async def _handle_start(
    websocket: WebSocket,
    task_id: str,
    data: dict[str, Any],
    llm,
) -> None:
    """触发一次流式生成。

    关键路径：
    1. 解析 task_id → GenerationTask → chapter_id
    2. 读取 task.params.mode/continue_from_chars/target_word_count
    3. 选择 Agent（按 task_type） + APIConfig
    4. 若 client 自带 messages（向后兼容旧前端），走 LLMService.stream_with_usage 直接流
    5. 否则委托 WriterAgent.build_messages 加载完整上下文,再调 llm.stream_with_usage
    6. partial_save 与 finalize 按 mode 分支(continue / generate)
    """
    override_messages: list[LLMMessage] | None = None
    if "messages" in data and data["messages"]:
        override_messages = [
            LLMMessage(role=m.get("role", "user"), content=m.get("content", ""))
            for m in data["messages"]
            if m.get("content")
        ]

    stream_id = str(uuid.uuid4())

    async with async_session_factory() as db:
        task = await _load_task(db, task_id)
        if task is None:
            await websocket.send_json({"type": "error", "error": f"task {task_id} 不存在"})
            return
        if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            await websocket.send_json({
                "type": "error",
                "error": f"task {task_id} 状态为 {task.status.value}，无法再次启动",
            })
            return

        chapter_id = task.chapter_id
        agent_type = AGENT_FOR_TASK.get(task.task_type, "writer")

        # 解析 APIConfig（找不到则走 mock）
        cfg = await resolve_provider_config(db, agent_type=agent_type)

        # 读取 mode 参数(由前端 chaptersApi.generate 写入 task.params)
        params = dict(task.params or {})
        mode = params.get("mode", "generate")
        if mode not in ("continue", "generate"):
            logger.warning("未知 mode=%s,回退到 generate", mode)
            mode = "generate"
        continue_from_chars = int(params.get("continue_from_chars", 1500))
        target_word_count = params.get("target_word_count")
        # [P3 增强] 读取 outline_node_id(可选);若前端未传,WriterAgent 内 fallback 到 chapter.outline_node_id
        outline_node_id = params.get("outline_node_id")
        if isinstance(outline_node_id, str):
            try:
                outline_node_id = uuid.UUID(outline_node_id)
            except ValueError:
                logger.warning("outline_node_id 不是合法 UUID: %r,忽略", outline_node_id)
                outline_node_id = None
        # [提交 C] 自动去味开关(默认开)
        auto_polish = bool(params.get("auto_polish", True))
        max_blocking_for_rewrite = int(params.get("max_blocking_for_rewrite", 0))
        # 文风关键词(从 work 取,供自动去味 prompt 使用)
        work_style_keywords: list[str] = []
        try:
            if chapter and chapter.work_id:
                from app.models.work import Work as _Work
                work_obj = await db.get(_Work, chapter.work_id)
                if work_obj and work_obj.style_keywords:
                    work_style_keywords = list(work_obj.style_keywords)
        except Exception:
            pass

        # 续写模式:取章节 baseline 一次性快照,后续所有写库操作基于此 baseline + 累计
        existing_baseline = ""
        if mode == "continue" and chapter_id is not None:
            r0 = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
            ch0 = r0.scalar_one_or_none()
            if ch0:
                existing_baseline = ch0.plain_content or ""

        # 标记 task 进入 running
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now(timezone.utc)
        await db.commit()

    await websocket.send_json({
        "type": "start",
        "task_id": task_id,
        "stream_id": stream_id,
        "agent": agent_type,
        "model": cfg.model if cfg else "mock",
        "provider": cfg.provider.value if cfg else "mock",
        "mode": mode,
    })

    full_content = ""
    final_usage: dict[str, int] = {"input_tokens": 0, "output_tokens": 0}
    error_msg: str | None = None
    prompt_used: str = ""

    try:
        async with async_session_factory() as db:
            # ===== 构建 LLMRequest =====
            if override_messages is not None:
                # 旧前端兼容:客户端自带 messages 时,跳过 DB 加载
                req = LLMRequest(
                    messages=override_messages,
                    model=data.get("model", cfg.model if cfg else "mock"),
                    temperature=float(data.get("temperature", 0.85)),
                    max_tokens=int(data.get("max_tokens", 2048)),
                    stream=True,
                )
                prompt_used = "(override:client_messages)"
            elif chapter_id is None:
                raise ValueError("task 未绑定 chapter,且客户端未提供 messages")
            else:
                # ===== 真实 writer 路径:由 WriterAgent 加载上下文并装配消息 =====
                # [提交 B] 在 build_messages 之前解析章节角色,
                # 透传到 WriterAgent 用于 Reference Gate 路由 references
                resolved_outline_id = outline_node_id
                if not resolved_outline_id and chapter_id is not None:
                    ch_for_role = await db.get(Chapter, chapter_id)
                    if ch_for_role:
                        resolved_outline_id = ch_for_role.outline_node_id
                outline_for_role = None
                if resolved_outline_id:
                    from app.models.outline import OutlineNode as _OutlineNode
                    outline_for_role = await db.get(_OutlineNode, resolved_outline_id)
                chapter_role = resolve_chapter_role(outline_for_role)

                agent = WriterAgent()
                messages, model_name, prompt_text = await agent.build_messages(
                    db,
                    chapter_id,
                    mode=mode,
                    continue_from_chars=continue_from_chars,
                    target_word_count=target_word_count,
                    outline_node_id=outline_node_id,
                    chapter_role=chapter_role,
                )
                req = LLMRequest(
                    messages=messages,
                    model=data.get("model", cfg.model if cfg else model_name),
                    temperature=float(data.get("temperature", 0.85)),
                    max_tokens=int(data.get("max_tokens", 4096)),
                    stream=True,
                )
                prompt_used = prompt_text

            # ===== 流式循环(stream_with_usage 携带 token 用量) =====
            buffer_size = 0
            flush_threshold = 200  # 字符,超过则节流写一次库
            last_sent_cleaned = ""  # 已发给前端的最大干净字符串,用于 diff
            async for delta, usage in llm.stream_with_usage(req, cfg):
                if delta:
                    full_content += delta
                    buffer_size += len(delta)
                    # 增量发干净 delta:重新清理全文,只把新增部分发给前端
                    # - 剥离 <think> 块 / 英文 thinking 行
                    # - 剔除 existing_tail 前缀(防止模型复读原章节正文)
                    new_cleaned = _strip_think_blocks(full_content, drop_prefix=existing_baseline)
                    clean_delta = new_cleaned[len(last_sent_cleaned):]
                    last_sent_cleaned = new_cleaned
                    if clean_delta:
                        await websocket.send_json({
                            "type": "delta",
                            "task_id": task_id,
                            "stream_id": stream_id,
                            "content": clean_delta,
                        })
                if usage:
                    # 取最后一个非空 usage(OpenAI 流末尾的 chunk 会带真实数字)
                    final_usage = usage
                if buffer_size >= flush_threshold and chapter_id is not None:
                    await _partial_save_chapter(
                        db,
                        chapter_id,
                        last_sent_cleaned,  # 写库版本也用干净文本
                        mode=mode,
                        existing_baseline=existing_baseline,
                    )
                    buffer_size = 0

    except Exception as e:
        logger.error("生成失败: task_id=%s, error=%s", task_id, e, exc_info=True)
        error_msg = str(e)

    # ===== 自动去味(在落库与回报前执行;失败兜底不阻断) =====
    auto_polish_report: dict | None = None
    if not error_msg and auto_polish:
        cleaned_full = _strip_think_blocks(full_content, drop_prefix=existing_baseline)
        cleaned_full, auto_polish_report = await _auto_polish_if_needed(
            text=cleaned_full,
            cfg=cfg,
            style_keywords=work_style_keywords,
            max_blocking_for_rewrite=max_blocking_for_rewrite,
        )
        # 把去味结果同步回 full_content,确保落库与前端一致
        full_content = cleaned_full

    # ===== 完成态落库 =====
    model_used = cfg.model if cfg else "mock"
    async with async_session_factory() as db:
        task = await _load_task(db, task_id)
        chapter_id = task.chapter_id if task else None
        if task:
            task.completed_at = datetime.now(timezone.utc)
            if error_msg:
                task.status = TaskStatus.FAILED
                task.error = error_msg[:2000]
            elif task.status == TaskStatus.CANCELLED:
                pass  # 用户已取消
            else:
                task.status = TaskStatus.COMPLETED
                # 预览内容也要剥离<think>痕迹
                preview_text = _strip_think_blocks(full_content)
                task.result = {
                    "preview": preview_text[:500],
                    "length": len(preview_text),
                    "mode": mode,
                    "auto_polish_report": auto_polish_report,
                }
            task.token_usage = final_usage
            await db.commit()

        # finalize:continue 模式追加段落 + 写 ChapterVersion,generate 模式全量覆盖
        if chapter_id and not error_msg:
            if mode == "continue":
                await _finalize_chapter_continuation(
                    db,
                    chapter_id,
                    new_content=full_content,
                    existing_baseline=existing_baseline,
                    prompt_used=prompt_used,
                    model_used=model_used,
                    token_usage=final_usage,
                )
            else:
                await _finalize_chapter(db, chapter_id, full_content)

    # ===== 给前端回报 =====
    if error_msg:
        await websocket.send_json({
            "type": "error",
            "task_id": task_id,
            "stream_id": stream_id,
            "error": error_msg,
        })
    else:
        # full_content 已经包含 think 剥离 + 自动去味结果,直接用
        await websocket.send_json({
            "type": "done",
            "task_id": task_id,
            "stream_id": stream_id,
            "content": full_content,
            "token_usage": final_usage,
            "mode": mode,
            "auto_polish_report": auto_polish_report,
        })


# ==================== 提交 C:自动去味(生成收尾阶段) ====================


# 单章重写后的最小有效长度,低于此值视为 LLM 没救(返回空/模板),保留原文
_AUTO_POLISH_MIN_OUTPUT_CHARS = 50


async def _auto_polish_if_needed(
    text: str,
    cfg: ProviderConfig | None,
    *,
    style_keywords: list[str] | None,
    max_blocking_for_rewrite: int = 0,
) -> tuple[str, dict | None]:
    """生成完成后:跑 AI 痕迹检测,blocking 超阈值就调 LLM 整章重写一次。

    返回: (final_text, report)。report=None 表示跳过(auto_polish 关闭或空文本)。

    报告字段:
    - blocking_count / advisory_count: 改写前
    - rewrite_attempted / rewrite_succeeded: bool
    - rewrite_error: str | None
    - final_blocking: 改写后剩余 blocking 数(None 表示未再检测)
    - pre_findings: list[dict] —— 改写前 findings 摘要(至多 5 条)
    - elapsed_ms: int
    """
    if not text or not text.strip():
        return text, None
    start_ms = int(time.time() * 1000)
    detector = AIPatternDetector()

    # ===== 阶段 1:检测 =====
    findings = detector.detect(text)
    blocking_count = sum(1 for f in findings if f.severity == Severity.BLOCKING)
    advisory_count = sum(1 for f in findings if f.severity == Severity.ADVISORY)

    base_report = {
        "blocking_count": blocking_count,
        "advisory_count": advisory_count,
        "rewrite_attempted": False,
        "rewrite_succeeded": False,
        "rewrite_error": None,
        "final_blocking": None,
        "pre_findings": [f.to_dict() for f in findings[:5]],
        "elapsed_ms": 0,
    }

    # 无 blocking → 不触发重写
    if blocking_count <= max_blocking_for_rewrite:
        base_report["elapsed_ms"] = int(time.time() * 1000) - start_ms
        return text, base_report

    # ===== 阶段 2:LLM 整章重写 =====
    base_report["rewrite_attempted"] = True
    system, user = build_rewrite_full_chapter_prompt(
        chapter_text=text,
        findings=findings,
        style_keywords=style_keywords,
    )
    model_name = cfg.model if cfg else "mock"
    req = LLMRequest(
        messages=[LLMMessage(role="system", content=system), LLMMessage(role="user", content=user)],
        model=model_name,
        temperature=0.5,
        max_tokens=4096,
        stream=False,
    )
    llm = get_llm_service()
    try:
        resp = await llm.chat(req, cfg)
        rewritten = (resp.content or "").strip()
    except LLMError as exc:
        logger.warning("自动去味: LLM 失败 (%s),保留原文", exc)
        base_report["rewrite_error"] = f"{exc.__class__.__name__}: {exc}"
        base_report["elapsed_ms"] = int(time.time() * 1000) - start_ms
        return text, base_report

    # ===== 阶段 3:验收 =====
    # 3a) 输出过短 → 视为没救,保留原文
    if len(rewritten) < _AUTO_POLISH_MIN_OUTPUT_CHARS:
        logger.warning(
            "自动去味: LLM 输出过短(%d 字),保留原文",
            len(rewritten),
        )
        base_report["rewrite_error"] = f"output_too_short: {len(rewritten)} chars"
        base_report["elapsed_ms"] = int(time.time() * 1000) - start_ms
        return text, base_report

    # 3b) 再跑一次检测,记录 remaining blocking
    post_findings = detector.detect(rewritten)
    final_blocking = sum(1 for f in post_findings if f.severity == Severity.BLOCKING)
    base_report["final_blocking"] = final_blocking
    base_report["elapsed_ms"] = int(time.time() * 1000) - start_ms
    base_report["rewrite_succeeded"] = True

    logger.info(
        "自动去味: blocking %d → %d (advisory %d → %d), elapsed %dms",
        blocking_count,
        final_blocking,
        advisory_count,
        sum(1 for f in post_findings if f.severity == Severity.ADVISORY),
        base_report["elapsed_ms"],
    )
    return rewritten, base_report


# ==================== 持久化辅助 ====================


async def _load_task(db, task_id: str) -> GenerationTask | None:
    try:
        tid = uuid.UUID(task_id)
    except ValueError:
        return None
    r = await db.execute(select(GenerationTask).where(GenerationTask.id == tid))
    return r.scalar_one_or_none()


async def _partial_save_chapter(
    db,
    chapter_id: uuid.UUID,
    full_content: str,
    *,
    mode: str = "generate",
    existing_baseline: str = "",
) -> None:
    """流式过程中节流写 plain_content（status 暂不更新为 generated）

    - mode="continue": plain_content = existing_baseline + full_content（保留原正文）
    - mode="generate": plain_content = full_content（覆盖）
    """
    r = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    ch = r.scalar_one_or_none()
    if not ch:
        return
    await db.refresh(ch)
    # 剥离思维链 / 推理痕迹,避免 <think>...</think> 污染正文;同时剔除 existing_tail 复述
    clean_content = _strip_think_blocks(full_content, drop_prefix=existing_baseline if mode == "continue" else None)
    if mode == "continue":
        ch.plain_content = existing_baseline + clean_content
    else:
        ch.plain_content = clean_content
    ch.word_count = count_words(ch.plain_content)
    await db.commit()


async def _finalize_chapter(db, chapter_id: uuid.UUID, full_content: str) -> None:
    """generate 模式完成时落库：content (单段 TipTap) + plain_content + word_count + status=generated + version++"""
    r = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    ch = r.scalar_one_or_none()
    if not ch:
        return
    clean = _strip_think_blocks(full_content)
    ch.plain_content = clean
    ch.word_count = count_words(clean)
    ch.content = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": clean}],
            }
        ],
    }
    ch.status = ChapterStatus.GENERATED
    ch.version = (ch.version or 0) + 1
    await db.commit()


async def _finalize_chapter_continuation(
    db,
    chapter_id: uuid.UUID,
    *,
    new_content: str,
    existing_baseline: str,
    prompt_used: str,
    model_used: str,
    token_usage: dict[str, int],
) -> None:
    """continue 模式完成时落库：TipTap doc 追加段落 + plain_content 拼接 + ChapterVersion(ai_revised) + version++"""
    r = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    ch = r.scalar_one_or_none()
    if not ch:
        return

    # 剥离 LLM 思维链(<think>...</think>) + 剔除 existing_tail 复述,保证入库正文干净
    clean_new_content = _strip_think_blocks(new_content, drop_prefix=existing_baseline)

    # 边缘情况:剥离后干净内容为空(< 10 字符)—— 模型把全部输出塞进了 think 块。
    # 此时放弃覆盖,回滚到 existing_baseline(避免把含 `` 的 partial-save 脏数据留下)。
    if len(clean_new_content.strip()) < 10:
        logger.warning(
            "finalize_chapter_continuation: cleaned new_content is empty/too short "
            "(raw=%d, clean=%d). Rolling back to baseline.",
            len(new_content), len(clean_new_content),
        )
        # 回滚 plain_content 到 baseline,不清掉原始内容
        ch.plain_content = existing_baseline
        ch.word_count = count_words(existing_baseline)
        await db.commit()
        # 不写 ChapterVersion,因为没有真实产出
        return

    # 防御:若 partial-save 没刷盘,这里用 baseline 兜底
    final_plain = (ch.plain_content or "") if (ch.plain_content or "").endswith(clean_new_content) else (existing_baseline + clean_new_content)
    if not final_plain.endswith(clean_new_content):
        final_plain = existing_baseline + clean_new_content

    # 追加 TipTap 段落(不动原有结构)
    new_chunk_doc = _split_plain_to_tiptap_doc(clean_new_content)
    new_doc = _append_paragraphs_to_tiptap(ch.content or {"type": "doc", "content": []}, clean_new_content)

    ch.plain_content = final_plain
    ch.word_count = count_words(final_plain)
    ch.content = new_doc
    ch.status = ChapterStatus.GENERATED
    ch.version = (ch.version or 0) + 1
    await db.commit()

    # 落档历史版本
    version = ChapterVersion(
        chapter_id=ch.id,
        version_no=ch.version,
        content=new_chunk_doc,
        plain_content=clean_new_content,
        generated_by="ai_revised",
        prompt_used=(prompt_used or "")[:5000],
        model_used=(model_used or "")[:100],
        token_usage=token_usage or {},
        note=f"AI 续写 +{len(clean_new_content)} 字",
    )
    db.add(version)
    await db.commit()


def _split_plain_to_tiptap_doc(plain: str) -> dict:
    """把纯文本切段,生成 TipTap doc({type:doc, content:[paragraph...]})。"""
    if not plain:
        return {"type": "doc", "content": []}
    blocks: list[str] = []
    current: list[str] = []
    for line in plain.split("\n"):
        if line.strip() == "":
            if current:
                blocks.append("\n".join(current))
                current = []
        else:
            current.append(line)
    if current:
        blocks.append("\n".join(current))
    return {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": block}],
            }
            for block in blocks
        ],
    }


# 思维链 / 推理痕迹剥离器 — 部分推理型 LLM(MiniMax / DeepSeek-R1 / Qwen-QwQ)
# 会把 <think>...</think> 块混进流式输出,污染正文。这里统一剥离并收敛空白。
#
# 四类污染:
#   1) 闭合的 <think>...</think> —— 严格正则剥离
#   2) 未闭合的 <think>(模型忘了写 </think> 就开始写正文)
#      → 从 <think> 起点剥离到首个空行 / end-of-string
#   3) 整段英文 thinking —— 启发式:不含任何中文字符的行整段丢弃
#   4) 复述 existing_tail —— 如果剥离后剩下的是已存在正文(模型复读输入),
#      直接剔除前缀,只留真正的新增内容
_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
_UNCLOSED_THINK_RE = re.compile(
    r"<think>.*?(?=\n\n|$)",
    re.DOTALL,
)
_NO_CN_LINE_RE = re.compile(
    r"^[^\n一-鿿]*[A-Za-z][^\n一-鿿]*$",
    re.MULTILINE,
)
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")


def _strip_think_blocks(text: str, drop_prefix: str | None = None) -> str:
    """从 LLM 输出中剥离 <think> 块、unclosed 思考泄漏、英文 thinking 行,
    可选地剔除 existing_tail 复述(防止模型复读输入,可在头部或尾部)。

    - 幂等:重复调用结果不变
    - 不抛异常:输入为空/异常时返回原值

    剥离策略(按顺序):
    1) 闭合 <think>...</think> 块
    2) 未闭合 <think> 块(到首个空行 / end-of-string)
    3) 行级:整行无 CJK 且含英文 → 丢弃
    4) 段落级:丢弃开头的英文 thinking 段(从前往后扫描,直到首个 CJK 占比 >= 50% 的段落)
    5) 末尾 existing_tail 复述剔除(检测 startswith / endswith + 模糊子串匹配)
    """
    if not text:
        return text
    try:
        cleaned = _THINK_BLOCK_RE.sub("", text)
        cleaned = _UNCLOSED_THINK_RE.sub("", cleaned)
        cleaned = _NO_CN_LINE_RE.sub("", cleaned)

        # 段落级剥离开头 thinking:直到首个 CJK >= 50% 的段落
        paragraphs = re.split(r"\n\n+", cleaned)
        start_idx = 0
        for i, p in enumerate(paragraphs):
            stripped = p.strip()
            if not stripped:
                continue
            cjk = len(re.findall(r"[一-鿿]", p))
            eng = len(re.findall(r"[A-Za-z]", p))
            total = cjk + eng
            if total > 0 and cjk / total >= 0.5:
                start_idx = i
                break
        else:
            # 全部段落都不是 CJK-dominant → 整体为 thinking
            cleaned = ""
        if cleaned != "":
            cleaned = "\n\n".join(paragraphs[start_idx:])

        cleaned = _MULTI_NEWLINE_RE.sub("\n\n", cleaned)

        # 复述剔除:头部 / 尾部 / 模糊子串
        if drop_prefix:
            tail = drop_prefix.strip()
            if cleaned.startswith(tail):
                cleaned = cleaned[len(tail):]
            elif cleaned.endswith(tail):
                cleaned = cleaned[: -len(tail)] if len(tail) > 0 else cleaned
            else:
                # 模糊匹配:模型可能截掉了 existing_tail 的开头/末尾,
                # 只复读中间一段。从长到短遍历 tail 的所有后缀长度,
                # 看它是否能作为 cleaned 的开头/结尾。最多 1 次全量循环,
                # 19 字 tail 也只跑 19 次。
                matched = False
                for n in range(len(tail), 0, -1):
                    sub = tail[-n:]
                    if cleaned.startswith(sub):
                        cleaned = cleaned[len(sub):]
                        matched = True
                        break
                    if cleaned.endswith(sub):
                        cleaned = cleaned[: -len(sub)]
                        matched = True
                        break
                # 中段匹配:找出 existing_tail 在 cleaned 中的位置,若是单纯的「前后是中文/空」
                # 也尝试切掉(避免模型在 draft 中插入了复述段)
                if not matched:
                    idx = cleaned.find(tail)
                    if idx == 0:
                        cleaned = cleaned[len(tail):]
                    # 出现在中段(不太常见)→ 保守不剥离,避免误删

        return cleaned.strip()
    except Exception:
        return text


def _append_paragraphs_to_tiptap(doc: dict, plain: str) -> dict:
    """把 plain 的段落追加到既有 TipTap doc 末尾(保留原 marks/attrs)。"""
    new_doc = _split_plain_to_tiptap_doc(plain)
    if not isinstance(doc, dict):
        doc = {"type": "doc", "content": []}
    existing = doc.get("content") or []
    return {**doc, "content": [*existing, *(new_doc.get("content") or [])]}


async def _cancel_task(task_id: str) -> None:
    """客户端断开或收到 cancel 时，把 task 标记为 cancelled。"""
    try:
        tid = uuid.UUID(task_id)
    except ValueError:
        return
    async with async_session_factory() as db:
        r = await db.execute(select(GenerationTask).where(GenerationTask.id == tid))
        t = r.scalar_one_or_none()
        if t and t.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
            t.status = TaskStatus.CANCELLED
            t.completed_at = datetime.now(timezone.utc)
            await db.commit()