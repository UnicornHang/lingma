"""Critic 评审 API"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.critic_agent import CriticAgent
from app.deps import get_db
from app.schemas.critic import (
    CriticEvaluateRequest,
    CriticEvaluateResponse,
)

router = APIRouter()


@router.post(
    "/critic/evaluate",
    response_model=CriticEvaluateResponse,
    summary="多 Persona 评审章节(单次 LLM 调用)",
)
async def critic_evaluate_endpoint(
    payload: CriticEvaluateRequest,
    db: AsyncSession = Depends(get_db),
) -> CriticEvaluateResponse:
    agent = CriticAgent()
    evaluation, _model_used = await agent.evaluate(
        db,
        work_id=payload.work_id,
        chapter_id=payload.chapter_id,
        content=payload.content,
        personas=payload.personas,
        extra_hint=payload.extra_hint,
    )
    return CriticEvaluateResponse(evaluation=evaluation)