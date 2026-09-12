"""Character Agent - 角色"""
from app.agents.base import BaseAgent


class CharacterAgent(BaseAgent):
    agent_type = "character"
    description = "设计人物档案：背景/性格/动机/人物弧"

    async def execute(self, context: dict) -> dict:
        return {
            "agent": self.agent_type,
            "characters": [],
            "message": "Character Agent MVP 占位输出",
        }