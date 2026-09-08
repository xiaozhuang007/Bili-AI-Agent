"""
B站 AI Agent - 应用入口
FastAPI 主应用，聚合路由
"""

import sys
from pathlib import Path

# 确保 backend 目录在 sys.path 中
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from config import Config
from services.utils import get_local_ip
from api import chat, download, cookie

# 创建 FastAPI 应用
app = FastAPI(
    title="Bilibili AI Agent",
    description="B站视频智能下载助手 - 用自然语言下载B站视频",
    version="1.0.0",
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat.router)
app.include_router(download.router)
app.include_router(cookie.router)

# 静态文件
frontend_dir = Config.BASE_DIR / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")


@app.get("/")
async def index():
    """返回前端页面"""
    index_path = Config.BASE_DIR / "frontend" / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "Bilibili AI Agent API", "docs": "/docs"}


@app.get("/api/health")
async def health():
    """健康检查"""
    return {"ok": True, "service": "bilibili-ai-agent"}


if __name__ == "__main__":
    import uvicorn

    ip = get_local_ip()
    print("=" * 50)
    print("  Bilibili AI Agent")
    print("=" * 50)
    print(f"  Local:  http://localhost:{Config.PORT}")
    print(f"  LAN:    http://{ip}:{Config.PORT}")
    print(f"  Docs:   http://localhost:{Config.PORT}/docs")
    print("=" * 50)

    uvicorn.run(app, host=Config.HOST, port=Config.PORT)
