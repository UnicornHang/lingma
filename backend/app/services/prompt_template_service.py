"""[P4] Prompt 模板服务 —— CRUD + 运行时解析。

设计:
- 每个 agent_type 一行;启动时 ensure_defaults 写入代码默认
- enabled=True 用库内 system_prompt;False 回退代码默认
- ``{{var}}`` 简单替换(不用 Jinja,避免注入风险)
"""
from __future__ import annotations

import logging
import re
from typing import Iterable

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prompt_template import PromptTemplate
from app.prompts.character_prompts import build_character_system_prompt
from app.prompts.critic_prompts import ALL_PERSONAS, build_critic_system_prompt
from app.prompts.editor_prompts import build_editor_system_prompt
from app.prompts.plot_prompts import build_plot_system_prompt
from app.prompts.world_prompts import build_world_system_prompt
from app.prompts.writer_prompts import WRITER_SYSTEM_TEMPLATE
from app.schemas.prompt_template import (
    AgentType,
    PromptTemplateRead,
    PromptTemplateUpdate,
)

logger = logging.getLogger(__name__)

AGENT_TYPES: tuple[AgentType, ...] = (
    "writer",
    "plot",
    "world",
    "character",
    "editor",
    "critic",
)

_AGENT_META: dict[str, dict[str, str]] = {
    "writer": {
        "name": "Writer 写作",
        "description": "章节正文生成的系统提示。可用占位符 {{target_words}}。",
        "variables": "target_words",
    },
    "plot": {
        "name": "Plot 大纲",
        "description": "卷→章→节拍大纲生成的系统提示。",
        "variables": "",
    },
    "world": {
        "name": "World 世界观",
        "description": "世界书六维建议的系统提示。",
        "variables": "",
    },
    "character": {
        "name": "Character 角色",
        "description": "角色卡批量设计的系统提示。",
        "variables": "",
    },
    "editor": {
        "name": "Editor 编辑",
        "description": "AI 痕迹去味改写的系统提示。",
        "variables": "",
    },
    "critic": {
        "name": "Critic 评审",
        "description": "多 Persona 评审的系统提示。可用 {{personas_block}} / {{persona_count}}。",
        "variables": "personas_block,persona_count",
    },
}

_VAR_PATTERN = re.compile(r"\{\{(\w+)\}\}")


def _default_system_prompt(agent_type: str) -> str:
    """从代码内置 builder 生成默认 system prompt(含占位符)。"""
    if agent_type == "writer":
        return WRITER_SYSTEM_TEMPLATE
    if agent_type == "plot":
        return build_plot_system_prompt()
    if agent_type == "world":
        return build_world_system_prompt()
    if agent_type == "character":
        return build_character_system_prompt()
    if agent_type == "editor":
        return build_editor_system_prompt()
    if agent_type == "critic":
        # 用占位符版本,运行时注入 persona 块
        sample = build_critic_system_prompt(ALL_PERSONAS)
        # 将动态 persona 段替换为占位符(取「【本次评审的 Persona】」到「【输出纪律」之间)
        marker_start = "【本次评审的 Persona】"
        marker_end = "【输出纪律"
        i = sample.find(marker_start)
        j = sample.find(marker_end)
        if i >= 0 and j > i:
            head = sample[: i + len(marker_start)]
            tail = sample[j:]
            # 同步替换开头人数
            head = re.sub(
                r"同时以 \d+ 种 Persona",
                "同时以 {{persona_count}} 种 Persona",
                head,
            )
            return f"{head}\n{{{{personas_block}}}}\n\n{tail}".strip()
        return sample
    raise ValueError(f"未知 agent_type: {agent_type}")


def render_placeholders(template: str, variables: dict[str, str] | None) -> str:
    """将 ``{{key}}`` 替换为 variables[key];缺失则保留原样。"""
    if not variables:
        return template

    def _repl(m: re.Match[str]) -> str:
        key = m.group(1)
        return variables.get(key, m.group(0))

    return _VAR_PATTERN.sub(_repl, template)


def _parse_variables(raw: str) -> list[str]:
    if not raw.strip():
        return []
    return [v.strip() for v in raw.split(",") if v.strip()]


def _to_read(row: PromptTemplate, default_text: str) -> PromptTemplateRead:
    return PromptTemplateRead(
        agent_type=row.agent_type,  # type: ignore[arg-type]
        name=row.name,
        description=row.description,
        system_prompt=row.system_prompt,
        enabled=row.enabled,
        variables=_parse_variables(row.variables),
        is_customized=row.system_prompt.strip() != default_text.strip(),
        updated_at=row.updated_at,
    )


async def ensure_defaults(db: AsyncSession) -> None:
    """幂等写入六个 Agent 的默认模板行。"""
    for agent_type in AGENT_TYPES:
        result = await db.execute(
            select(PromptTemplate).where(PromptTemplate.agent_type == agent_type)
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            continue
        meta = _AGENT_META[agent_type]
        db.add(
            PromptTemplate(
                agent_type=agent_type,
                name=meta["name"],
                description=meta["description"],
                system_prompt=_default_system_prompt(agent_type),
                enabled=True,
                variables=meta["variables"],
            )
        )
    await db.flush()


async def list_templates(db: AsyncSession) -> list[PromptTemplateRead]:
    """列出全部 Agent 模板。"""
    await ensure_defaults(db)
    result = await db.execute(select(PromptTemplate))
    rows = {r.agent_type: r for r in result.scalars().all()}
    items: list[PromptTemplateRead] = []
    for agent_type in AGENT_TYPES:
        row = rows[agent_type]
        items.append(_to_read(row, _default_system_prompt(agent_type)))
    return items


async def get_template(db: AsyncSession, agent_type: str) -> PromptTemplateRead:
    """获取单个模板。"""
    if agent_type not in AGENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未知 Agent: {agent_type}",
        )
    await ensure_defaults(db)
    result = await db.execute(
        select(PromptTemplate).where(PromptTemplate.agent_type == agent_type)
    )
    row = result.scalar_one()
    return _to_read(row, _default_system_prompt(agent_type))


async def update_template(
    db: AsyncSession, agent_type: str, payload: PromptTemplateUpdate
) -> PromptTemplateRead:
    """更新模板内容或启用状态。"""
    if agent_type not in AGENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未知 Agent: {agent_type}",
        )
    await ensure_defaults(db)
    result = await db.execute(
        select(PromptTemplate).where(PromptTemplate.agent_type == agent_type)
    )
    row = result.scalar_one()
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(row, k, v)
    await db.flush()
    await db.refresh(row)
    return _to_read(row, _default_system_prompt(agent_type))


async def reset_template(db: AsyncSession, agent_type: str) -> PromptTemplateRead:
    """重置为代码内置默认,并启用。"""
    if agent_type not in AGENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未知 Agent: {agent_type}",
        )
    await ensure_defaults(db)
    result = await db.execute(
        select(PromptTemplate).where(PromptTemplate.agent_type == agent_type)
    )
    row = result.scalar_one()
    meta = _AGENT_META[agent_type]
    row.system_prompt = _default_system_prompt(agent_type)
    row.enabled = True
    row.name = meta["name"]
    row.description = meta["description"]
    row.variables = meta["variables"]
    await db.flush()
    await db.refresh(row)
    return _to_read(row, _default_system_prompt(agent_type))


async def resolve_system_prompt(
    db: AsyncSession | None,
    agent_type: str,
    *,
    variables: dict[str, str] | None = None,
    fallback: str | None = None,
) -> str:
    """运行时解析:启用的自定义模板优先,否则用 fallback/代码默认。"""
    fb = fallback if fallback is not None else _default_system_prompt(agent_type)
    fb_rendered = render_placeholders(fb, variables)

    if db is None:
        return fb_rendered

    try:
        await ensure_defaults(db)
        result = await db.execute(
            select(PromptTemplate).where(PromptTemplate.agent_type == agent_type)
        )
        row = result.scalar_one_or_none()
        if row is None or not row.enabled:
            return fb_rendered
        return render_placeholders(row.system_prompt, variables)
    except Exception as exc:  # noqa: BLE001 — 解析失败不阻断生成
        logger.warning("解析 Prompt 模板失败(%s),回退默认: %s", agent_type, exc)
        return fb_rendered


def build_personas_block(personas: Iterable[str]) -> str:
    """供 Critic 注入的 Persona 说明块。"""
    from app.prompts.critic_prompts import get_persona_instruction

    return "\n\n".join(
        f"### {p}\n{get_persona_instruction(p)}" for p in personas
    )
