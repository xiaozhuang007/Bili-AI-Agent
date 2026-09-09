# Bilibili AI Agent

B站视频智能下载助手 —— 用自然语言下载B站视频的 Agent Web 应用。

基于 LangChain + FastAPI 构建，将传统下载工具升级为 AI Agent 应用。

## 功能

- **对话式下载**：发送B站链接 + 自然语言，Agent 自动下载
- **智能状态查询**：问"下载好了吗"、"我下了哪些视频"，Agent 直接回答
- **Cookie 管理**：对话中检测 Cookie 状态、提示更新
- **文件级 Cookie 检测/转换**：把浏览器导出的 Cookie 文件放进 `cookie_imports/`，Agent 自动识别格式（Netscape/浏览器字符串/JSON）、检测关键字段、**实测登录态**，一键转换为可用格式并生效
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
├── cookie_imports/          # 用户导出 Cookie 文件的共享目录（挂载进容器）
├── shared/                  # 通用共享目录（挂载进容器，可给 Agent 读任意文件）
├── downloads/               # 下载文件目录
├── cookie.txt               # 生效 Cookie 文件（由 Agent 维护）
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
| check_cookie_status | 检查当前生效 Cookie 状态 |
| update_cookie | 粘贴内容更新 Cookie |
| read_file | 读取共享目录中的文件（安全白名单） |
| check_cookie_file | 检测 Cookie 文件可用性（格式+字段+实测登录） |
| convert_cookie_file | 转换 Cookie 文件为 Netscape 并设为生效 |
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

部分B站视频需要登录才能下载。Cookie 支持三种格式，Agent 自动识别：

- **Netscape 格式**：yt-dlp 标准格式，开箱即用
- **浏览器字符串格式**：`name=value; name2=value2; ...`（自动转换）
- **JSON 格式**：EditThisCookie / Cookie-Editor 等浏览器扩展导出的数组格式（自动转换）

### 文件级检测/转换流程

1. 浏览器扩展导出 Cookie 文件 → 放入 `cookie_imports/` 目录
2. 对话中告诉 Agent 文件名（如 `帮我检测 99.json`）
3. Agent 检测：格式识别 → 关键字段检查 → 过期时间 → **实测登录态**（请求 B站 API）
4. 需要时让 Agent 转换：输出 Netscape 副本 `xxx_netscape.txt` + 设为当前生效 Cookie

> 原始文件永远不会被修改；Cookie 含敏感凭据，已通过 .gitignore 排除，不会上传。

## License

MIT
