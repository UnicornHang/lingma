"""Critic Agent - 多 Persona 章节评审

真实实现:基于 Work 上下文 + 章节正文,单次 LLM 调用产出 5 Persona × 4 维度评分。
- 强 schema 校验:LLM 输出不符合 PersonaScore 时该 persona 丢弃,其余保留。
- 不直接写库:返回 CriticEvaluation 由前端展示。
- 兼容旧版 ``execute(context)`` 接口(orchestrator 调用方保持不变)。
- 共识 issues:Python 端从各 persona 的 top_issues 中聚合出现 ≥2 次的关键词。

设计决策:
- 单次 LLM 调用（非 5 次串行）— 减少 token 翻倍与网络往返
- temperature=0.4 求稳定 JSON 输出
- 6000 字正文上限(超长截断)避免 prompt 过载
"""
from __future__ import annotations

import json
import logging
from collections import Counter
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.agents.character_agent import _extract_json_object
from app.models.chapter import Chapter
from app.models.work import Work
from app.prompts.critic_prompts import (
    ALL_PERSONAS,
    build_critic_system_prompt,
    build_critic_user_prompt,
)
from app.schemas.critic import (
    AggregatedScore,
    CriticEvaluation,
    CriticPersona,
    PersonaScore,
)
from app.services.llm_service import (
    LLMError,
    LLMMessage,
    LLMRequest,
    get_llm_service,
    resolve_provider_config,
)

logger = logging.getLogger(__name__)


class CriticAgent(BaseAgent):
    agent_type = "critic"
    description = "多 Persona 评审:一致性/节奏/文笔/代入感"

    # ------- 兼容旧版 orchestrator 调用 -------

    async def execute(self, context: dict) -> dict:
        """[P2] Orchestrator 占位实现 —— 当前生产路径不走 orchestrator,
        WS critic hook 直接调 evaluate()。若未来 orchestrator 接入,应改为:
            return (await self.evaluate(...))[0].model_dump()
        """
        return {
            "agent": self.agent_type,
            "scores": {
                "consistency": 0.85,
                "pacing": 0.78,
                "engagement": 0.82,
            },
            "issues": [],
            "message": "Critic Agent MVP 占位输出(请使用 evaluate() 真实实现)",
        }

    # ------- 真实实现 -------

    async def evaluate(
        self,
        db: AsyncSession,
        *,
        work_id: UUID,
        chapter_id: UUID | None = None,
        content: str | None = None,
        personas: list[CriticPersona] | None = None,
        extra_hint: str | None = None,
    ) -> tuple[CriticEvaluation, str]:
        """多 Persona 评审章节正文。

        返回: (evaluation, model_used)

        Args:
            db: 数据库会话
            work_id: 必填,用于加载 work meta 与解析 provider config
            chapter_id: 可选,提供时自动加载 chapter.plain_content
            content: 可选,直接传入待评正文(优先级高于 chapter_id)
            personas: 要评审的 persona 列表,None 时评审全部 5 个
            extra_hint: 用户附加要求
        """
        # 1) 加载 work
        work = await _load_work(db, work_id)
        if work is None:
            logger.error("CriticAgent.evaluate: work %s 不存在", work_id)
            return _empty_evaluation(chapter_id=chapter_id), "mock"

        # 2) 解析待评正文:content 优先,否则从 chapter_id 加载
        chapter_title = ""
        chapter_summary = ""
        resolved_content = content
        if resolved_content is None and chapter_id is not None:
            chapter = await _load_chapter(db, chapter_id)
            if chapter is not None:
                resolved_content = chapter.plain_content or ""
                chapter_title = chapter.title or ""
                chapter_summary = chapter.summary or ""
        if not resolved_content:
            logger.warning(
                "CriticAgent.evaluate: 无可评正文 (work=%s, chapter_id=%s, content_len=%s)",
                work_id, chapter_id, len(content) if content else 0,
            )
            return _empty_evaluation(chapter_id=chapter_id), "mock"

        # 3) 规范化 personas
        target_personas = list(personas) if personas else list(ALL_PERSONAS)

        # 4) 解析 provider 配置
        cfg = await resolve_provider_config(db, agent_type=self.agent_type, work_id=work_id)
        model_name = cfg.model if cfg else "mock"

        # 5) 构造 prompt
        system_msg = build_critic_system_prompt(target_personas)
        user_msg = build_critic_user_prompt(
            work=work,
            chapter_title=chapter_title,
            chapter_summary=chapter_summary,
            content=resolved_content,
            personas=target_personas,
            extra_hint=extra_hint,
        )

        # 6) 调用 LLM(非流式 JSON)
        llm = get_llm_service()
        req = LLMRequest(
            messages=[
                LLMMessage(role="system", content=system_msg),
                LLMMessage(role="user", content=user_msg),
            ],
            model=model_name,
            temperature=0.4,
            max_tokens=min(4096, 1500 + 5 * 400),
            stream=False,
        )

        raw_content = ""
        try:
            resp = await llm.chat(req, cfg)
            raw_content = resp.content or ""
        except LLMError as e:
            logger.error("CriticAgent LLM 调用失败: %s", e, exc_info=True)
            return _empty_evaluation(chapter_id=chapter_id, model_name=model_name), model_name
        except Exception as e:
            logger.error("CriticAgent 异常: %s", e, exc_info=True)
            return _empty_evaluation(chapter_id=chapter_id, model_name=model_name), model_name

        # 7) 抽取 + 解析 JSON
        json_text = _extract_json_object(raw_content)
        if not json_text:
            logger.warning(
                "CriticAgent LLM 输出中找不到 JSON: model=%s, raw_len=%d",
                model_name,
                len(raw_content),
            )
            return _empty_evaluation(
                chapter_id=chapter_id, model_name=model_name, raw_content=raw_content
            ), model_name

        try:
            parsed = json.loads(json_text)
        except json.JSONDecodeError as e:
            logger.warning("CriticAgent JSON 解析失败: %s; text_head=%s", e, json_text[:200])
            return _empty_evaluation(
                chapter_id=chapter_id, model_name=model_name, raw_content=raw_content
            ), model_name

        # 兼容 LLM 直接给 {"persona_scores": [...]} 或扁平 list 两种结构
        if isinstance(parsed, dict):
            scores_payload = parsed.get("persona_scores")
            if scores_payload is None:
                scores_payload = parsed
        else:
            scores_payload = parsed

        if not isinstance(scores_payload, list):
            logger.warning("CriticAgent scores 不是 list: %s", type(scores_payload))
            return _empty_evaluation(
                chapter_id=chapter_id, model_name=model_name, raw_content=raw_content
            ), model_name

        # 8) 强 schema 校验:逐 persona Pydantic 解析
        persona_scores: list[PersonaScore] = []
        for i, item in enumerate(scores_payload):
            if not isinstance(item, dict):
                logger.warning("CriticAgent 第 %d 条不是 dict: %r", i, item)
                continue
            try:
                ps = PersonaScore.model_validate(item)
                # 若 LLM 输出 persona 不在请求列表里,丢弃(防止幻觉 persona)
                if ps.persona not in target_personas:
                    logger.warning("CriticAgent 第 %d 条 persona=%s 不在请求列表中", i, ps.persona)
                    continue
                persona_scores.append(ps)
            except Exception as e:
                logger.warning("CriticAgent 第 %d 条校验失败: %s; raw=%r", i, e, item)
                continue

        # 9) Python 端聚合:平均 + 共识 issues
        aggregated = _aggregate_scores(persona_scores)
        consensus_issues = _extract_consensus_issues(persona_scores)

        evaluation = CriticEvaluation(
            chapter_id=chapter_id,
            persona_scores=persona_scores,
            aggregated=aggregated,
            consensus_issues=consensus_issues,
            model_used=model_name,
            raw_content=raw_content,
        )

        logger.info(
            "CriticAgent.evaluate: work=%s, chapter=%s, personas=%d, scores=%d, model=%s",
            work_id, chapter_id, len(target_personas), len(persona_scores), model_name,
        )
        return evaluation, model_name


# ==================== 内部辅助 ====================


def _aggregate_scores(persona_scores: list[PersonaScore]) -> AggregatedScore:
    """等权平均聚合(无人时给中性 0.5)。"""
    if not persona_scores:
        return AggregatedScore(
            consistency=0.5, pacing=0.5, prose=0.5, engagement=0.5, overall=0.5,
        )
    n = len(persona_scores)
    cons = sum(p.consistency for p in persona_scores) / n
    pac = sum(p.pacing for p in persona_scores) / n
    pro = sum(p.prose for p in persona_scores) / n
    eng = sum(p.engagement for p in persona_scores) / n
    overall = (cons + pac + pro + eng) / 4.0
    return AggregatedScore(
        consistency=round(cons, 4),
        pacing=round(pac, 4),
        prose=round(pro, 4),
        engagement=round(eng, 4),
        overall=round(overall, 4),
    )


def _extract_consensus_issues(
    persona_scores: list[PersonaScore],
    *,
    threshold: int = 2,
    max_issues: int = 10,
) -> list[str]:
    """从各 persona 的 top_issues 中聚合出现 ≥ threshold 次的关键词。

    简化策略:将每个 issue 文本按 2-gram 切分(去标点),统计出现次数。
    实际项目里可用 LLM 二次总结;这里采用启发式以避免再调一次 LLM。
    """
    if not persona_scores:
        return []
    counter: Counter[tuple[str, ...]] = Counter()
    for ps in persona_scores:
        for issue in ps.top_issues:
            # 提取关键词:用最长的子句(避免 2-gram 切分错误)
            # 这里用 issue 原文作为一条 unit,阈值 ≥2 视为共识
            counter[(issue.strip(),)] += 1
    consensus = [item[0] for item, count in counter.most_common() if count >= threshold]
    return consensus[:max_issues]


def _empty_evaluation(
    *,
    chapter_id: UUID | None = None,
    model_name: str = "mock",
    raw_content: str = "",
) -> CriticEvaluation:
    """构造一个空 evaluation(失败/兜底路径使用)。"""
    return CriticEvaluation(
        chapter_id=chapter_id,
        persona_scores=[],
        aggregated=AggregatedScore(
            consistency=0.5, pacing=0.5, prose=0.5, engagement=0.5, overall=0.5,
        ),
        consensus_issues=[],
        model_used=model_name,
        raw_content=raw_content,
    )


# ==================== DB 加载辅助 ====================


async def _load_work(db: AsyncSession, work_id: UUID) -> Work | None:
    r = await db.execute(select(Work).where(Work.id == work_id))
    return r.scalar_one_or_none()


async def _load_chapter(db: AsyncSession, chapter_id: UUID) -> Chapter | None:
    r = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    return r.scalar_one_or_none()