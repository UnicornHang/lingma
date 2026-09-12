"""Writer Agent - 章节正文写作"""
from app.agents.base import BaseAgent


class WriterAgent(BaseAgent):
    agent_type = "writer"
    description = "基于大纲 + 上下文生成章节正文"

    async def execute(self, context: dict) -> dict:
        chapter_id = context.get("chapter_id")
        target_words = context.get("target_word_count", 3000)
        return {
            "agent": self.agent_type,
            "chapter_id": str(chapter_id) if chapter_id else None,
            "content": f"[Writer 占位] 已根据上下文规划 {target_words} 字章节内容...",
            "word_count": 0,
            "message": "Writer Agent MVP 占位输出",
        }