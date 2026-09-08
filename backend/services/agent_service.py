"""
Agent 服务模块
使用 LangChain 1.x create_agent 构建 B站下载助手 Agent
"""

from langchain_openai import ChatOpenAI
from langchain.agents import create_agent

from config import Config
from tools.agent_tools import ALL_TOOLS

# 系统提示词
SYSTEM_PROMPT = """You are a Bilibili video download assistant (B站视频下载助手).

Your capabilities:
1. Download Bilibili videos from URLs
2. Check download progress and status
3. List downloaded files and download history
4. Get video information (title, uploader, duration, views)
5. Check and manage Cookie status
6. Update Cookie when needed

Guidelines:
- When a user provides a Bilibili URL, use download_video to start the download
- After starting a download, tell the user the task_id so they can check progress
- If a download fails, check Cookie status and suggest updating it
- When listing files or tasks, format the output clearly
- Be helpful and concise
- If the user asks about a video but doesn't provide a URL, ask for one
- Always respond in the same language as the user (Chinese or English)

Remember: You are a download assistant, not a general chatbot. Focus on download-related tasks.
"""


class AgentService:
    """Agent 服务，管理 LangChain Agent 实例和对话历史"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=Config.LLM_MODEL,
            api_key=Config.SILICONFLOW_API_KEY,
            base_url=Config.LLM_BASE_URL,
            temperature=0.7,
            timeout=60,
        )

        self.agent = create_agent(
            model=self.llm,
            tools=ALL_TOOLS,
            system_prompt=SYSTEM_PROMPT,
        )

    def chat(self, message: str, history: list = None) -> dict:
        """
        对话接口

        Args:
            message: 用户消息
            history: 对话历史 [{"role": "user/assistant", "content": "..."}]

        Returns:
            {"reply": "...", "history": [...]}
        """
        # 构建消息列表
        messages = []
        if history:
            for h in history:
                messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": message})

        # 调用 Agent
        result = self.agent.invoke({"messages": messages})

        # 取最后一条 AI 消息
        ai_reply = result["messages"][-1].content

        # 更新历史
        new_history = (history or []).copy()
        new_history.append({"role": "user", "content": message})
        new_history.append({"role": "assistant", "content": ai_reply})

        return {
            "reply": ai_reply,
            "history": new_history,
        }


# 全局单例
agent_service = AgentService()
