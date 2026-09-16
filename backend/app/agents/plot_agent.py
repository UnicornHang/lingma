"""Plot Agent - 剧情规划

真实实现：基于 Work 上下文生成 N 卷 × M 章的大纲建议（不强写入 DB）。
- 强 schema 校验：LLM 输出不符合 PlotVolume 时返回空 list,不抛 500。
- 调用方按需把返回的 volumes 通过 `POST /works/{id}/bulk-create` 落库。
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.agents.character_agent import (  # 复用 JSON 抽取逻辑
    _extract_json_object,
    _strip_llm_think,
)
from app.agents.plot_outline_parse import (
    OUTLINE_VOLUME_ATTEMPTS,
    _normalize_inner_ascii_quotes,
    parse_one_volume,
    parse_outline_volumes,
)
from app.models.outline import OutlineNode, OutlineNodeType
from app.models.work import Work
from app.prompts.plot_prompts import (
    build_plot_expand_system_prompt,
    build_plot_expand_user_prompt,
    build_plot_one_volume_user_prompt,
    build_plot_system_prompt,
    split_chapter_counts,
)
from app.schemas.outline import (
    PlotChapterExpand,
    PlotChapterExpandResponse,
    PlotOutlineResponse,
    PlotVolume,
)
from app.services import tracking_service
from app.services.knowledge_scope import format_knowledge_brief
from app.services.llm_service import (
    LLMError,
    LLMMessage,
    LLMRequest,
    ProviderConfig,
    get_llm_service,
    resolve_provider_config,
    thinking_extra_body,
)

logger = logging.getLogger(__name__)


@dataclass
class OutlineGenSession:
    """一次大纲生成的共享上下文：按卷多次调用 LLM。"""

    work: object
    cfg: ProviderConfig | None
    model_name: str
    system_msg: str
    extra_hint: str | None
    total_volumes: int
    chapter_counts: list[int]


class PlotAgent(BaseAgent):
    """剧情 Agent:负责总纲/卷纲/章纲/节拍设计"""

    agent_type = "plot"
    description = "规划故事大纲、章节节拍、伏笔体系"

    # ------- 兼容旧版 orchestrator 调用 -------

    async def execute(self, context: dict) -> dict:
        work_id = context.get("work_id")
        logline = context.get("logline", "")
        return {
            "agent": self.agent_type,
            "work_id": str(work_id) if work_id else None,
            "volumes": [
                {
                    "title": "第一卷 · 序章",
                    "chapters": 10,
                    "beats": ["开场", "激励事件", "第一情节点", "中场", "高潮"],
                },
            ],
            "input_logline": logline,
            "message": "Plot Agent MVP 占位输出(请使用 generate_outline() 真实实现)",
        }

    # ------- 真实实现 -------

    async def prepare_outline_session(
        self,
        db: AsyncSession,
        *,
        work_id: UUID | None = None,
        work: "Work | None" = None,
        total_volumes: int = 3,
        target_chapter_count: int | None = None,
        extra_hint: str | None = None,
    ) -> OutlineGenSession | None:
        """解析作品与模型配置，供按卷生成使用。"""
        resolved_work: "Work | None" = None
        if work_id is not None:
            resolved_work = await _load_work(db, work_id)
            if resolved_work is None:
                logger.error("PlotAgent.prepare_outline_session: work %s 不存在", work_id)
                return None
        elif work is not None:
            resolved_work = work
        else:
            logger.error("PlotAgent.prepare_outline_session: 必须提供 work_id 或 work")
            return None

        if target_chapter_count is None:
            word_target = resolved_work.target_word_count or 100_000
            target_chapter_count = max(5, min(200, word_target // 3000))
        target_chapter_count = max(1, min(200, target_chapter_count))
        total_volumes = max(1, min(10, total_volumes))

        cfg = await resolve_provider_config(db, agent_type=self.agent_type, work_id=work_id)
        model_name = cfg.model if cfg else "mock"
        # 单卷 JSON 合同以代码内提示为准，不用库里可能仍要求「一次吐完全书」的旧模板
        return OutlineGenSession(
            work=resolved_work,
            cfg=cfg,
            model_name=model_name,
            system_msg=build_plot_system_prompt(),
            extra_hint=extra_hint,
            total_volumes=total_volumes,
            chapter_counts=split_chapter_counts(target_chapter_count, total_volumes),
        )

    def make_one_volume_request(
        self,
        session: OutlineGenSession,
        vol_index: int,
        prior_volumes: list[PlotVolume],
        *,
        attempt: int = 0,
    ) -> LLMRequest:
        """构造第 vol_index 卷（0-based）的 LLM 请求。"""
        vol_no = vol_index + 1
        chapter_count = session.chapter_counts[vol_index]
        chapter_start = 1 + sum(session.chapter_counts[:vol_index])
        prior = [(v.vol_no, v.vol_title, v.summary or "") for v in prior_volumes]
        retry_note = None
        if attempt > 0:
            retry_note = (
                f"只要第 {vol_no} 卷的 JSON。"
                "第一个字符是 { ，不要分析。"
            )
        user_msg = build_plot_one_volume_user_prompt(
            work=session.work,  # type: ignore[arg-type]
            vol_no=vol_no,
            total_volumes=session.total_volumes,
            chapter_count=chapter_count,
            chapter_start=chapter_start,
            extra_hint=session.extra_hint,
            prior_volumes=prior or None,
            retry_note=retry_note,
        )
        temperature = max(0.15, 0.35 - 0.1 * attempt)
        max_tokens = min(16_384, 8_192 + 4_096 * attempt)
        return LLMRequest(
            messages=[
                LLMMessage(role="system", content=session.system_msg),
                LLMMessage(role="user", content=user_msg),
            ],
            model=session.model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            extra=self._thinking_extra(session.cfg, session.model_name),
        )

    def _thinking_extra(self, cfg: ProviderConfig | None, model_name: str) -> dict | None:
        """MiniMax-M3 默认开启 think，会把 max_tokens 吃在思考上导致 JSON 写不完。"""
        return thinking_extra_body(cfg, model_name)

    async def generate_outline(
        self,
        db: AsyncSession,
        *,
        work_id: UUID | None = None,
        work: "Work | None" = None,
        total_volumes: int = 3,
        target_chapter_count: int | None = None,
        extra_hint: str | None = None,
    ) -> tuple[PlotOutlineResponse, str]:
        """生成卷→章两层大纲建议(不写库)。

        按卷多次调用 LLM：60 章一次 JSON 会被截断，每轮只生成 1 卷。

        - ``work_id`` 优先：从 DB 加载已有 Work
        - 否则 ``work`` 必须提供（允许前端预览场景,work 尚未入库）
        - 都未提供：返回空列表,日志记录原因

        返回: (response, model_used)
        - response: 强 schema 校验通过的 PlotOutlineResponse;失败时 volumes=[]
        - model_used: 实际调用的模型名
        """
        session = await self.prepare_outline_session(
            db,
            work_id=work_id,
            work=work,
            total_volumes=total_volumes,
            target_chapter_count=target_chapter_count,
            extra_hint=extra_hint,
        )
        if session is None:
            return PlotOutlineResponse(volumes=[]), "mock"

        llm = get_llm_service()
        volumes: list[PlotVolume] = []
        raw_parts: list[str] = []
        for i in range(len(session.chapter_counts)):
            parsed_vol: PlotVolume | None = None
            last_raw = ""
            for attempt in range(OUTLINE_VOLUME_ATTEMPTS):
                req = self.make_one_volume_request(session, i, volumes, attempt=attempt)
                req.stream = False
                try:
                    resp = await llm.chat(req, session.cfg)
                    last_raw = resp.content or ""
                except LLMError as e:
                    logger.error("PlotAgent 第 %d 卷 LLM 失败: %s", i + 1, e, exc_info=True)
                    continue
                except Exception as e:
                    logger.error("PlotAgent 第 %d 卷异常: %s", i + 1, e, exc_info=True)
                    continue
                parsed_vol = parse_one_volume(last_raw, i + 1)
                if parsed_vol is not None:
                    break
                logger.warning(
                    "PlotAgent 第 %d 卷第 %d 次解析为空 raw_len=%d",
                    i + 1, attempt + 1, len(last_raw),
                )
            raw_parts.append(last_raw)
            if parsed_vol is None:
                logger.warning("PlotAgent 第 %d 卷多次失败，停止后续卷以免跳号", i + 1)
                break
            volumes.append(parsed_vol)

        raw_content = "\n".join(raw_parts)
        if not volumes:
            logger.warning(
                "PlotAgent 大纲解析为空: model=%s, raw_len=%d",
                session.model_name, len(raw_content),
            )
        logger.info(
            "PlotAgent.generate_outline: work=%s, total_volumes=%s, target_chapters=%s, model=%s, generated=%d",
            work_id, session.total_volumes, sum(session.chapter_counts),
            session.model_name, len(volumes),
        )
        return PlotOutlineResponse(
            volumes=volumes, model_used=session.model_name, raw_content=raw_content,
        ), session.model_name

    async def expand_chapter_outline(
        self,
        db: AsyncSession,
        *,
        node,
        extra_hint: str | None = None,
    ) -> tuple[PlotChapterExpandResponse | None, str]:
        """扩写单章细纲建议（不写库）。失败返回 (None, model)。"""
        if node.type == OutlineNodeType.VOLUME:
            logger.warning("PlotAgent.expand_chapter_outline: 拒绝扩写卷纲 %s", node.id)
            return None, "mock"

        work = await _load_work(db, node.work_id)
        if work is None:
            logger.error("PlotAgent.expand_chapter_outline: work %s 不存在", node.work_id)
            return None, "mock"

        parent_title = ""
        if node.parent_id:
            parent = await db.get(OutlineNode, node.parent_id)
            if parent is not None:
                parent_title = parent.title or ""

        knowledge_brief = ""
        try:
            ledger = await tracking_service.get_or_create_tracking(db, node.work_id)
            knowledge_brief = format_knowledge_brief(ledger.payload, max_chars=1200)
        except Exception as exc:  # noqa: BLE001
            logger.warning("扩写细纲时加载账本失败: %s", exc)

        constraints = node.write_constraints if isinstance(node.write_constraints, dict) else {}
        if not constraints and hasattr(node.write_constraints, "model_dump"):
            constraints = node.write_constraints.model_dump()
        cfg = await resolve_provider_config(db, agent_type=self.agent_type, work_id=node.work_id)
        model_name = cfg.model if cfg else "mock"
        user_msg = build_plot_expand_user_prompt(
            work=work,
            node_title=node.title,
            node_type=node.type.value if hasattr(node.type, "value") else str(node.type),
            summary=node.summary or "",
            beats=list(node.beats or []),
            characters_involved=list(node.characters_involved or []),
            target_word_count=node.target_word_count or 3000,
            constraints=constraints,
            parent_title=parent_title,
            knowledge_brief=knowledge_brief,
            extra_hint=extra_hint,
        )
        llm = get_llm_service()
        raw_content = ""
        last_error: Exception | None = None
        for attempt in range(2):
            req = LLMRequest(
                messages=[
                    LLMMessage(role="system", content=build_plot_expand_system_prompt()),
                    LLMMessage(role="user", content=user_msg),
                ],
                model=model_name,
                temperature=max(0.25, 0.45 - 0.15 * attempt),
                max_tokens=4096 if attempt == 0 else 6144,
                stream=False,
                extra=self._thinking_extra(cfg, model_name),
            )
            try:
                resp = await llm.chat(req, cfg)
                raw_content = resp.content or ""
            except LLMError as e:
                last_error = e
                logger.error("PlotAgent 扩写细纲 LLM 失败 attempt=%d: %s", attempt, e, exc_info=True)
                continue
            except Exception as e:
                last_error = e
                logger.error("PlotAgent 扩写细纲异常 attempt=%d: %s", attempt, e, exc_info=True)
                continue
            suggestion = parse_expand_payload(raw_content)
            if suggestion is not None:
                return (
                    PlotChapterExpandResponse(
                        suggestion=suggestion,
                        model_used=model_name,
                        raw_content=raw_content,
                    ),
                    model_name,
                )
            logger.warning(
                "PlotAgent 扩写细纲 JSON 无效 attempt=%d raw_len=%d preview=%s",
                attempt, len(raw_content), (raw_content or "")[:240],
            )
        if last_error is not None and not raw_content:
            logger.error("PlotAgent 扩写细纲最终失败: %s", last_error)
        return None, model_name


def parse_expand_payload(raw_content: str) -> PlotChapterExpand | None:
    """从 LLM 原文抽出 PlotChapterExpand；夹 think / 截断时尽量 salvage。"""
    json_text = _extract_json_object(raw_content or "")
    stripped = _strip_llm_think(raw_content or "") or raw_content
    candidates = [t for t in (json_text, stripped, raw_content) if t]
    seen: set[str] = set()
    for text in candidates:
        if text in seen:
            continue
        seen.add(text)
        parsed = _load_expand_dict(text)
        if parsed is None:
            continue
        if "volumes" in parsed and "title" not in parsed:
            continue
        payload = dict(parsed)
        if isinstance(payload.get("summary"), str):
            payload["summary"] = _normalize_inner_ascii_quotes(payload["summary"])
        try:
            return PlotChapterExpand.model_validate(payload)
        except Exception as e:
            logger.warning("PlotChapterExpand 校验失败: %s", e)
            continue
    return None


def _load_expand_dict(text: str) -> dict | None:
    """json.loads 失败时，仍尝试抽出含 title 的对象。"""
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    if start < 0:
        return None
    snippet = text[start:]
    try:
        parsed = json.loads(snippet)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass
    # 截断：补一个闭合括号再试一次
    for closer in ("}", "]}", "}}"):
        try:
            parsed = json.loads(snippet.rstrip().rstrip(",") + closer)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and parsed.get("title"):
            return parsed
    return None


# ==================== DB 加载辅助 ====================


async def _load_work(db: AsyncSession, work_id: UUID) -> Work | None:
    r = await db.execute(select(Work).where(Work.id == work_id))
    return r.scalar_one_or_none()
