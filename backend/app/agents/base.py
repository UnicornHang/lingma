"""Agent 基类"""
from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """所有 Agent 的基类"""

    agent_type: str = "base"
    description: str = "Base agent"

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs

    @abstractmethod
    async def execute(self, context: dict) -> dict:
        """执行 Agent 任务"""
        raise NotImplementedError