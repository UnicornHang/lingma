"""Plot Agent - 剧情规划"""
from app.agents.base import BaseAgent


class PlotAgent(BaseAgent):
    """剧情 Agent：负责总纲/卷纲/章纲/节拍设计"""

    agent_type = "plot"
    description = "规划故事大纲、章节节拍、伏笔体系"

    async def execute(self, context: dict) -> dict:
        work_id = context.get("work_id")
        logline = context.get("logline", "")
        # MVP 占位：返回固定结构
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
            "message": "Plot Agent MVP 占位输出",
        }