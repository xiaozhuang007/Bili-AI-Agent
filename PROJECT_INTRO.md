# B站视频智能下载助手 — 项目介绍（200字版）

> 基于 LangChain + FastAPI 构建，用自然语言对话控制 B站视频下载的 AI Agent。

**技术栈**：LangChain 1.x Agent 框架 + FastAPI 后端 + yt-dlp 下载核心 + 原生 HTML/JS 前端 + Docker 容器化。

**架构**：六层分层——路由层（FastAPI 接口）→ Agent 层（LangChain create_agent）→ 工具层（@tool 装饰器）→ 业务层（下载/Cookie/通用工具）→ 配置层 → 入口层。

**核心流程**：用户发一句自然语言 → FastAPI 接收 → Agent 解析意图 → 调用 download_video/get_status 等 Tool → yt-dlp 执行下载 → Agent 返回自然语言结果。

**开发步骤**：①核心业务（yt-dlp 封装）②工具层（@tool）③Agent 组装④前端界面⑤容器化部署⑥安全加固（密钥外置 .env 管理）。改代码重启容器，改依赖需重建。
