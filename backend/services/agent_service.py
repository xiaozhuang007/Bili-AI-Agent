"""
Agent 服务模块
使用 LangChain 1.x create_agent + MemorySaver (checkpointer) 实现 B站下载助手 Agent
窗口记忆：只保留最近 5 轮对话，省 token，不持久化（内存存储，重启清空）
"""

from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver

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
- If the user is just chatting (not asking for downloads), respond normally as a conversational assistant

Remember: You are a download assistant, not a general chatbot. But you can chat normally when not handling download tasks.

Important - Memory Limit: You can only remember the last 5 rounds of conversation (10 messages). Older messages are automatically forgotten. If a user asks about something from many rounds ago, you should let them know you don't have that in memory.
"""

# 窗口大小：只保留最近 N 轮对话（1 轮 = 1 user + 1 assistant）
WINDOW_K = 5


class AgentService:
    """Agent 服务，管理 LangChain Agent 实例和窗口记忆"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=Config.LLM_MODEL,
            api_key=Config.SILICONFLOW_API_KEY,
            base_url=Config.LLM_BASE_URL,
            temperature=0.7,
            timeout=60,
        )

        # MemorySaver: LangGraph 内置的内存 checkpointer
        # 每个 thread_id 对应一个独立的对话历史，互不干扰
        self.checkpointer = MemorySaver()

        # 创建 Agent，绑定 checkpointer 实现自动记忆
        self.agent = create_agent(
            model=self.llm,
            tools=ALL_TOOLS,
            system_prompt=SYSTEM_PROMPT,
            checkpointer=self.checkpointer,
        )

    def chat(self, message: str, session_id: str) -> dict:
        """
        对话接口（后端管理记忆，前端只需传 message + session_id）

        Args:
            message: 用户消息
            session_id: 会话 ID（前端生成，用作 thread_id）

        Returns:
            {"reply": "...", "session_id": "..."}
        """
        # 调用 Agent，通过 thread_id 区分会话
        # checkpointer 自动保存历史，下次调用同一 thread_id 时自动加载
        result = self.agent.invoke(
            {"messages": [{"role": "user", "content": message}]},
            config={"configurable": {"thread_id": session_id}},
        )

        # 取最后一条 AI 消息
        ai_reply = result["messages"][-1].content

        # 窗口裁剪：只保留最近 WINDOW_K 轮对话
        self._trim_history(session_id)

        return {
            "reply": ai_reply,
            "session_id": session_id,
        }

    def _trim_history(self, session_id: str):
        """窗口记忆：只保留最近 WINDOW_K 轮（WINDOW_K*2 条消息）"""
        try:
            # 从 checkpointer 获取当前会话的状态
            config = {"configurable": {"thread_id": session_id}}
            state = self.checkpointer.get(config)

            if state is None:
                return

            messages = state.get("messages", [])
            max_messages = WINDOW_K * 2  # 1 轮 = user + assistant = 2 条

            if len(messages) > max_messages:
                # 只保留最近 max_messages 条
                trimmed = messages[-max_messages:]
                # 更新 checkpointer 中的状态
                state["messages"] = trimmed
                # MemorySaver 用 put 方法更新
                self.checkpointer.put(config, state, {
                    "source": "update",
                    "step": -1,
                    "writes": {},
                })
        except Exception:
            # 裁剪失败不影响正常对话
            pass


# 全局单例
agent_service = AgentService()
