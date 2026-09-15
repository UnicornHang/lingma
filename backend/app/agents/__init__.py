"""AI Agent 实现"""
from app.agents.base import BaseAgent
from app.agents.character_agent import CharacterAgent
from app.agents.critic_agent import CriticAgent
from app.agents.editor_agent import EditorAgent
from app.agents.plot_agent import PlotAgent
from app.agents.style_mimic_agent import StyleMimicAgent
from app.agents.world_agent import WorldAgent
from app.agents.writer_agent import WriterAgent

__all__ = [
    "BaseAgent",
    "PlotAgent",
    "WorldAgent",
    "CharacterAgent",
    "WriterAgent",
    "EditorAgent",
    "CriticAgent",
    "StyleMimicAgent",
]


# Agent 类型 -> 实现类的注册表（用于工厂方法）
AGENT_REGISTRY: dict[str, type[BaseAgent]] = {
    "plot": PlotAgent,
    "world": WorldAgent,
    "character": CharacterAgent,
    "writer": WriterAgent,
    "editor": EditorAgent,
    "critic": CriticAgent,
    "style_mimic": StyleMimicAgent,
}


def create_agent(agent_type: str, **kwargs) -> BaseAgent:
    """工厂方法：根据类型创建 Agent 实例"""
    cls = AGENT_REGISTRY.get(agent_type)
    if not cls:
        raise ValueError(f"未知 Agent 类型: {agent_type}. 支持: {list(AGENT_REGISTRY)}")
    return cls(**kwargs)