"""
下载路由
提供下载相关的 REST API（保留原有接口，兼容非 Agent 调用）
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from config import Config
from services.download_service import download_service
from services.utils import extract_bilibili_url, get_cookie_path
from services.cookie_utils import is_netscape_format, convert_to_netscape, analyze_cookie

router = APIRouter(prefix="/api/download", tags=["download"])


class DownloadRequest(BaseModel):
    url: str


@router.post("/start")
async def start_download(req: DownloadRequest):
    """启动下载"""
    url = extract_bilibili_url(req.url)
    if not url:
        raise HTTPException(status_code=400, detail="Invalid Bilibili URL")

    info = download_service.get_video_info(url)
    if not info:
        raise HTTPException(status_code=400, detail="Cannot get video info")

    task_id = download_service.start_download(url, info['title'])
    return {"ok": True, "task_id": task_id, "title": info['title']}


@router.get("/status/{task_id}")
async def get_status(task_id: str):
    """查询下载状态"""
    task = download_service.get_status(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"ok": True, **task}


@router.get("/history")
async def get_history():
    """获取下载历史"""
    files = download_service.list_downloads()
    return {"files": files}


@router.get("/file/{task_id}")
async def download_file(task_id: str):
    """下载文件"""
    task = download_service.get_status(task_id)
    if not task or task["status"] != "done":
        raise HTTPException(status_code=404, detail="File not ready")

    filepath = Config.DOWNLOAD_DIR / task["filename"]
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(filepath, filename=task["filename"])
