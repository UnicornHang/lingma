"""编排引擎（Orchestrator）

MVP：基于预定义 DAG 串行调用 6 个 Agent。
     后续可替换为 LangGraph 状态机实现更复杂的分支与回滚。
"""
import logging
from typing import Any, Callable, Awaitable

from app.agents import AGENT_REGISTRY, create_agent

logger = logging.getLogger(__name__)


class Orchestrator:
    """编排器：协调多个 Agent 完成创作任务"""

    # 默认流水线：plot → world → character → writer → editor → critic
    DEFAULT_PIPELINE = ["plot", "world", "character", "writer", "editor", "critic"]

    def __init__(self) -> None:
        self.registry = dict(AGENT_REGISTRY)

    async def run_pipeline(
        self,
        context: dict[str, Any],
        *,
        pipeline: list[str] | None = None,
        on_progress: Callable[[str, dict], Awaitable[None]] | None = None,
    ) -> dict[str, Any]:
        """执行完整流水线

        Args:
            context: 初始上下文（work_id, logline, target_word_count, ...）
            pipeline: Agent 名称列表，默认六 Agent
            on_progress: 进度回调，签名 async (agent_name, partial_result) -> None
        Returns:
            最终结果字典，包含每个 Agent 的输出
        """
        pipeline = pipeline or self.DEFAULT_PIPELINE
        results: dict[str, Any] = {"_pipeline": pipeline, "_stages": {}}

        for agent_name in pipeline:
            if agent_name not in self.registry:
                logger.warning(f"未知 Agent 跳过: {agent_name}")
                continue

            logger.info(f"[Orchestrator] 运行 {agent_name} Agent")
            try:
                agent = create_agent(agent_name)
                stage_context = {**context, "previous_results": results["_stages"]}
                output = await agent.execute(stage_context)
                results["_stages"][agent_name] = output
                if on_progress:
                    await on_progress(agent_name, output)
            except Exception as e:
                logger.error(f"[Orchestrator] {agent_name} 失败: {e}", exc_info=True)
                results["_stages"][agent_name] = {"error": str(e)}
                results["_failed"] = agent_name
                break

        return results

    async def run_single(
        self,
        agent_name: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """运行单个 Agent"""
        if agent_name not in self.registry:
            raise ValueError(f"未知 Agent: {agent_name}")
        agent = create_agent(agent_name)
        return await agent.execute(context)


_orchestrator: Orchestrator | None = None


def get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator