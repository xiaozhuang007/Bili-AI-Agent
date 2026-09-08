# Bilibili AI Agent

B站视频智能下载助手 —— 用自然语言下载B站视频的 Agent Web 应用。

基于 LangChain + FastAPI 构建，将传统下载工具升级为 AI Agent 应用。

## 功能

- **对话式下载**：发送B站链接 + 自然语言，Agent 自动下载
- **智能状态查询**：问"下载好了吗"、"我下了哪些视频"，Agent 直接回答
- **Cookie 管理**：对话中检测 Cookie 状态、提示更新
- **视频信息查询**：发送链接，Agent 返回标题/UP主/时长等信息
- **多轮对话记忆**：Agent 记住上下文，支持连续追问

## 技术栈

| 层 | 技术 | 说明 |
|----|------|------|
| AI 框架 | LangChain 1.x | Agent + Tool + Memory |
| LLM | DeepSeek-V4-Pro (硅基流动) | 兼容 OpenAI API |
| 后端 | FastAPI | 异步 API |
| 前端 | HTML/CSS/JS | 轻量对话界面 |
| 下载核心 | yt-dlp | 视频下载 |
| 部署 | Docker | 容器化 |

## 项目结构

```
bilibili-ai-agent/
├── backend/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置管理
│   ├── api/                 # 路由层
│   │   ├── chat.py          # 对话接口
│   │   ├── download.py      # 下载接口
│   │   └── cookie.py        # Cookie 接口
│   ├── services/            # 业务逻辑层
│   │   ├── agent_service.py # Agent 服务
│   │   ├── download_service.py # 下载服务
│   │   ├── cookie_utils.py  # Cookie 工具
│   │   └── utils.py         # 通用工具
│   └── tools/               # Agent 工具层
│       └── agent_tools.py   # LangChain @tool 定义
├── frontend/
│   └── index.html           # 对话界面
├── downloads/               # 下载文件目录
├── cookie.txt               # Cookie 文件
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## 快速开始

### Docker 部署（推荐）

```bash
docker compose up -d --build
```

访问：`http://localhost:8000`

### 本地运行

```bash
pip install -r requirements.txt
cd backend
python main.py
```

## Agent 工具

| 工具名 | 功能 |
|--------|------|
| download_video | 下载B站视频 |
| get_download_status | 查询下载进度 |
| list_downloads | 列出已下载文件 |
| get_video_info | 获取视频信息 |
| check_cookie_status | 检查 Cookie 状态 |
| update_cookie | 更新 Cookie |
| list_all_tasks | 列出所有下载任务 |

## 对话示例

```
用户：帮我下载 https://www.bilibili.com/video/BV1xxx
Agent：正在获取视频信息... 标题是"xxx"，开始下载！任务ID: a1b2c3d4

用户：下载好了吗？
Agent：已下载完成！文件大小 120MB。

用户：我之前下了哪些视频？
Agent：你最近下载了 35 个视频，最新的是：1. xxx（120MB）...
```

## Cookie 说明

部分B站视频需要登录才能下载。Cookie 支持两种格式：

- **Netscape 格式**：浏览器插件导出
- **浏览器字符串格式**：`name=value; name2=value2; ...`（自动转换）

## License

MIT
