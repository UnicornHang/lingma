"""Plot Agent - 剧情规划

真实实现：基于 Work 上下文生成 N 卷 × M 章的大纲建议（不强写入 DB）。
- 强 schema 校验：LLM 输出不符合 PlotVolume 时返回空 list,不抛 500。
- 调用方按需把返回的 volumes 通过 `POST /works/{id}/bulk-create` 落库。
"""
from __future__ import annotations

import json
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.agents.character_agent import _extract_json_object  # 复用 JSON 抽取逻辑
from app.models.outline import OutlineNode, OutlineNodeType
from app.models.work import Work
from app.prompts.plot_prompts import (
    build_plot_expand_system_prompt,
    build_plot_expand_user_prompt,
    build_plot_system_prompt,
    build_plot_user_prompt,
)
from app.schemas.outline import PlotChapterExpand, PlotChapterExpandResponse, PlotOutlineResponse
from app.services import prompt_template_service, tracking_service
from app.services.knowledge_scope import format_knowledge_brief
from app.services.llm_service import (
    LLMError,
    LLMMessage,
    LLMRequest,
    get_llm_service,
    resolve_provider_config,
)

logger = logging.getLogger(__name__)


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

        - ``work_id`` 优先：从 DB 加载已有 Work
        - 否则 ``work`` 必须提供（允许前端预览场景,work 尚未入库）
        - 都未提供：返回空列表,日志记录原因

        返回: (response, model_used)
        - response: 强 schema 校验通过的 PlotOutlineResponse;失败时 volumes=[]
        - model_used: 实际调用的模型名
        """
        # 1) 解析 work:DB 优先,内存对象次之
        resolved_work: "Work | None" = None
        if work_id is not None:
            resolved_work = await _load_work(db, work_id)
            if resolved_work is None:
                logger.error("PlotAgent.generate_outline: work %s 不存在", work_id)
                return PlotOutlineResponse(volumes=[]), "mock"
        elif work is not None:
            resolved_work = work
        else:
            logger.error("PlotAgent.generate_outline: 必须提供 work_id 或 work")
            return PlotOutlineResponse(volumes=[]), "mock"

        # 2) 计算总章节数:未指定则按 work.target_word_count 推
        if target_chapter_count is None:
            word_target = resolved_work.target_word_count or 100_000
            target_chapter_count = max(5, min(200, word_target // 3000))
        target_chapter_count = max(1, min(200, target_chapter_count))

        # 3) 解析 provider 配置(work_id=None 时 fallback 全局默认)
        cfg = await resolve_provider_config(db, agent_type=self.agent_type, work_id=work_id)
        model_name = cfg.model if cfg else "mock"

        # 4) 构造 prompt
        system_msg = await prompt_template_service.resolve_system_prompt(
            db,
            "plot",
            fallback=build_plot_system_prompt(),
        )
        user_msg = build_plot_user_prompt(
            work=resolved_work,
            total_volumes=total_volumes,
            target_chapter_count=target_chapter_count,
            extra_hint=extra_hint,
        )

        # 5) 调用 LLM(非流式 JSON)
        llm = get_llm_service()
        req = LLMRequest(
            messages=[
                LLMMessage(role="system", content=system_msg),
                LLMMessage(role="user", content=user_msg),
            ],
            model=model_name,
            temperature=0.7,
            max_tokens=min(8192, 1200 + target_chapter_count * 180),
            stream=False,
        )

        raw_content = ""
        try:
            resp = await llm.chat(req, cfg)
            raw_content = resp.content or ""
        except LLMError as e:
            logger.error("PlotAgent LLM 调用失败: %s", e, exc_info=True)
            return PlotOutlineResponse(volumes=[], model_used=model_name), model_name
        except Exception as e:
            logger.error("PlotAgent 异常: %s", e, exc_info=True)
            return PlotOutlineResponse(volumes=[], model_used=model_name), model_name

        # 6) 抽取 + 解析 JSON
        json_text = _extract_json_object(raw_content)
        if not json_text:
            logger.warning(
                "PlotAgent LLM 输出中找不到 JSON: model=%s, raw_len=%d",
                model_name, len(raw_content),
            )
            return PlotOutlineResponse(volumes=[], model_used=model_name, raw_content=raw_content), model_name

        try:
            parsed = json.loads(json_text)
        except json.JSONDecodeError as e:
            logger.warning("PlotAgent JSON 解析失败: %s; text_head=%s", e, json_text[:200])
            return PlotOutlineResponse(volumes=[], model_used=model_name, raw_content=raw_content), model_name

        # 兼容 LLM 直接给 list 或 {volumes: [...]} 两种结构
        volumes_payload = parsed.get("volumes") if isinstance(parsed, dict) else parsed
        if not isinstance(volumes_payload, list):
            logger.warning("PlotAgent JSON.volumes 不是 list: %s", type(volumes_payload))
            return PlotOutlineResponse(volumes=[], model_used=model_name, raw_content=raw_content), model_name

        # 7) 强 schema 校验:逐卷 Pydantic 解析
        from app.schemas.outline import PlotVolume

        volumes: list[PlotVolume] = []
        for i, item in enumerate(volumes_payload):
            if not isinstance(item, dict):
                logger.warning("PlotAgent 第 %d 卷不是 dict: %r", i, item)
                continue
            try:
                volumes.append(PlotVolume.model_validate(item))
            except Exception as e:
                logger.warning("PlotAgent 第 %d 卷校验失败: %s; raw=%r", i, e, item)
                continue

        logger.info(
            "PlotAgent.generate_outline: work=%s, total_volumes=%s, target_chapters=%s, model=%s, generated=%d",
            work_id, total_volumes, target_chapter_count, model_name, len(volumes),
        )
        return PlotOutlineResponse(
            volumes=volumes, model_used=model_name, raw_content=raw_content,
        ), model_name

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
        req = LLMRequest(
            messages=[
                LLMMessage(role="system", content=build_plot_expand_system_prompt()),
                LLMMessage(role="user", content=user_msg),
            ],
            model=model_name,
            temperature=0.6,
            max_tokens=2048,
            stream=False,
        )
        raw_content = ""
        try:
            resp = await llm.chat(req, cfg)
            raw_content = resp.content or ""
        except LLMError as e:
            logger.error("PlotAgent 扩写细纲 LLM 失败: %s", e, exc_info=True)
            return None, model_name
        except Exception as e:
            logger.error("PlotAgent 扩写细纲异常: %s", e, exc_info=True)
            return None, model_name

        suggestion = parse_expand_payload(raw_content)
        if suggestion is None:
            logger.warning("PlotAgent 扩写细纲 JSON 无效: raw_len=%d", len(raw_content))
            return None, model_name
        return (
            PlotChapterExpandResponse(
                suggestion=suggestion,
                model_used=model_name,
                raw_content=raw_content,
            ),
            model_name,
        )


def parse_expand_payload(raw_content: str) -> PlotChapterExpand | None:
    """从 LLM 原文抽出 PlotChapterExpand；失败返回 None。"""
    json_text = _extract_json_object(raw_content or "")
    if not json_text:
        return None
    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    try:
        return PlotChapterExpand.model_validate(parsed)
    except Exception:
        return None


# ==================== DB 加载辅助 ====================


async def _load_work(db: AsyncSession, work_id: UUID) -> Work | None:
    r = await db.execute(select(Work).where(Work.id == work_id))
    return r.scalar_one_or_none()
