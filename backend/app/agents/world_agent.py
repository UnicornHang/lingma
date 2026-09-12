"""World Agent - 世界观"""
from app.agents.base import BaseAgent


class WorldAgent(BaseAgent):
    agent_type = "world"
    description = "构建世界书：地理/势力/修炼体系/魔法规则"

    async def execute(self, context: dict) -> dict:
        return {
            "agent": self.agent_type,
            "world_bible": {
                "geography": [],
                "factions": [],
                "magic_system": {},
                "history": [],
            },
            "message": "World Agent MVP 占位输出",
        }