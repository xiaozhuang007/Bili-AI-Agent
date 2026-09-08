"""
对话路由
提供 Agent 对话接口
前端只需传 message + session_id，后端自动管理对话历史
"""

from fastapi import APIRouter
from pydantic import BaseModel

from services.agent_service import agent_service

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    session_id: str


class ChatResponse(BaseModel):
    reply: str
    session_id: str


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """对话接口（后端管理记忆，前端只传 message + session_id）"""
    result = agent_service.chat(req.message, req.session_id)
    return ChatResponse(**result)
