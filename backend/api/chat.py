"""
对话路由
提供 Agent 对话接口（支持流式和非流式）
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from services.agent_service import agent_service

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    history: Optional[list] = []


class ChatResponse(BaseModel):
    reply: str
    history: list


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """非流式对话接口"""
    result = agent_service.chat(req.message, req.history)
    return ChatResponse(**result)
