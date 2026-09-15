"""World Agent - 世界观设计

真实实现:基于 Work 上下文 + 已有世界书内容,调用 LLM 生成 6 维度(geography/factions/
power_system/timeline/rules/culture)的世界书建议。
- 强 schema 校验:LLM 输出不符合 WorldBibleSuggestion 时返回空对象,不抛 500。
- 不直接写库:返回建议由前端按需合并到 WorldBible 对应的 JSON 字段。
- 兼容旧版 ``execute(context)`` 接口(orchestrator 调用方保持不变)。
"""
from __future__ import annotations

import json
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.agents.character_agent import _extract_json_object
from app.models.work import Work
from app.models.world import WorldBible
from app.prompts.world_prompts import build_world_system_prompt, build_world_user_prompt
from app.services import prompt_template_service
from app.schemas.world import WorldBibleSuggestion
from app.services.llm_service import (
    LLMError,
    LLMMessage,
    LLMRequest,
    get_llm_service,
    resolve_provider_config,
)

logger = logging.getLogger(__name__)


class WorldAgent(BaseAgent):
    agent_type = "world"
    description = "构建世界书:地理/势力/力量体系/历史/规则/文化 6 维度"

    # ------- 兼容旧版 orchestrator 调用 -------

    async def execute(self, context: dict) -> dict:
        work_id = context.get("work_id")
        return {
            "agent": self.agent_type,
            "work_id": str(work_id) if work_id else None,
            "world_bible": {
                "geography": {},
                "factions": {},
                "power_system": {},
                "timeline": {},
                "rules": {},
                "culture": {},
            },
            "message": "World Agent MVP 占位输出(请使用 suggest() 真实实现)",
        }

    # ------- 真实实现 -------

    async def suggest(
        self,
        db: AsyncSession,
        *,
        work_id: UUID,
        focus_dimension: str = "all",
        extra_hint: str | None = None,
    ) -> tuple[WorldBibleSuggestion, str, str]:
        """生成 6 维度世界书建议。

        返回: (suggestion, model_used, raw_content)
        - suggestion: 强 schema 校验通过的 WorldBibleSuggestion;失败时为默认空对象
        - model_used: 实际调用的模型名("mock" 表示走 mock provider)
        - raw_content: LLM 原始输出,便于调试
        """
        # 1) 加载 work
        work = await _load_work(db, work_id)
        if work is None:
            logger.error("WorldAgent.suggest: work %s 不存在", work_id)
            return WorldBibleSuggestion(), "mock", ""

        # 2) 加载已有世界书(若有,作为 prompt 上下文)
        existing_world = await _load_existing_world(db, work_id)

        # 3) 构造 prompt
        system_msg = await prompt_template_service.resolve_system_prompt(
            db,
            "world",
            fallback=build_world_system_prompt(),
        )
        user_msg = build_world_user_prompt(
            work=work,
            existing_world=existing_world,
            focus_dimension=focus_dimension,
            extra_hint=extra_hint,
        )

        # 4) 解析 provider 配置
        cfg = await resolve_provider_config(db, agent_type=self.agent_type, work_id=work_id)
        model_name = cfg.model if cfg else "mock"

        # 5) 调用 LLM(非流式 JSON)
        llm = get_llm_service()
        req = LLMRequest(
            messages=[
                LLMMessage(role="system", content=system_msg),
                LLMMessage(role="user", content=user_msg),
            ],
            model=model_name,
            temperature=0.75,
            max_tokens=8192,  # 6 维度输出量较大,给固定 8192
            stream=False,
        )

        raw_content = ""
        try:
            resp = await llm.chat(req, cfg)
            raw_content = resp.content or ""
        except LLMError as e:
            logger.error("WorldAgent LLM 调用失败: %s", e, exc_info=True)
            return WorldBibleSuggestion(), model_name, raw_content
        except Exception as e:
            logger.error("WorldAgent 异常: %s", e, exc_info=True)
            return WorldBibleSuggestion(), model_name, raw_content

        # 6) 抽取 + 解析 JSON
        json_text = _extract_json_object(raw_content)
        if not json_text:
            logger.warning(
                "WorldAgent LLM 输出中找不到 JSON: model=%s, raw_len=%d",
                model_name,
                len(raw_content),
            )
            return WorldBibleSuggestion(), model_name, raw_content

        try:
            parsed = json.loads(json_text)
        except json.JSONDecodeError as e:
            logger.warning(
                "WorldAgent JSON 解析失败: %s; text_head=%s",
                e,
                json_text[:200],
            )
            return WorldBibleSuggestion(), model_name, raw_content

        # 兼容 LLM 直接给 {"suggestion": {...}} 或扁平结构两种
        if isinstance(parsed, dict):
            suggestion_payload = parsed.get("suggestion")
            if suggestion_payload is None:
                # 没有 suggestion 键 → 整个 parsed 当作 suggestion
                suggestion_payload = parsed
        else:
            suggestion_payload = parsed
        if not isinstance(suggestion_payload, dict):
            logger.warning(
                "WorldAgent JSON.suggestion 不是 dict: %s", type(suggestion_payload)
            )
            return WorldBibleSuggestion(), model_name, raw_content

        # 7) 强 schema 校验:整个对象一次 model_validate
        #    WorldBibleSuggestion 顶层 extra="ignore",LLM 意外字段不会阻断
        #    单维度如果 LLM 给 list 而非 dict,会自动 coerce 失败 → 该维度保持 {}
        try:
            suggestion = WorldBibleSuggestion.model_validate(suggestion_payload)
        except Exception as e:
            logger.warning("WorldSuggestion 校验失败: %s; raw=%r", e, suggestion_payload)
            # 兜底:逐维度提取合法的 dict
            safe = WorldBibleSuggestion()
            for dim in ("geography", "factions", "power_system", "timeline", "rules", "culture"):
                v = suggestion_payload.get(dim)
                if isinstance(v, dict):
                    setattr(safe, dim, v)
            return safe, model_name, raw_content

        logger.info(
            "WorldAgent.suggest: work=%s, focus=%s, model=%s, dims_with_data=%s",
            work_id,
            focus_dimension,
            model_name,
            [k for k in ("geography", "factions", "power_system", "timeline", "rules", "culture")
             if getattr(suggestion, k)],
        )
        return suggestion, model_name, raw_content


# ==================== DB 加载辅助 ====================


async def _load_work(db: AsyncSession, work_id: UUID) -> Work | None:
    r = await db.execute(select(Work).where(Work.id == work_id))
    return r.scalar_one_or_none()


async def _load_existing_world(db: AsyncSession, work_id: UUID) -> WorldBible | None:
    """加载该作品的世界书(可能为 None)。失败时不抛,降级返回 None。"""
    try:
        r = await db.execute(select(WorldBible).where(WorldBible.work_id == work_id))
        wb = r.scalar_one_or_none()
        return wb
    except Exception as e:
        logger.warning("WorldAgent 加载已有世界书失败(降级): %s", e)
        return None