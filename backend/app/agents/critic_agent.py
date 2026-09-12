"""Critic Agent - 审稿"""
from app.agents.base import BaseAgent


class CriticAgent(BaseAgent):
    agent_type = "critic"
    description = "评估质量：人物一致性/节奏/OOC/逻辑漏洞"

    async def execute(self, context: dict) -> dict:
        return {
            "agent": self.agent_type,
            "scores": {
                "consistency": 0.85,
                "pacing": 0.78,
                "engagement": 0.82,
            },
            "issues": [],
            "message": "Critic Agent MVP 占位输出",
        }