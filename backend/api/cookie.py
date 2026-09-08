"""
Cookie 路由
提供 Cookie 管理 REST API
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

from config import Config
from services.download_service import download_service
from services.cookie_utils import is_netscape_format, convert_to_netscape, analyze_cookie

router = APIRouter(prefix="/api/cookie", tags=["cookie"])


class CookieSaveRequest(BaseModel):
    content: str


@router.get("")
async def get_cookie_status():
    """获取 Cookie 状态"""
    return download_service.get_cookie_status()


@router.post("")
async def set_cookie(req: Request):
    """上传/设置 Cookie（兼容文件上传和 JSON）"""
    content_type = req.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        form = await req.form()
        file = form.get("cookie_file")
        text = form.get("cookie_text", "")
        if file:
            raw = await file.read()
            try:
                content = raw.decode("utf-8").strip()
            except UnicodeDecodeError:
                content = raw.decode("latin-1").strip()
        elif text:
            content = text.strip()
        else:
            raise HTTPException(status_code=400, detail="No cookie content provided")
    else:
        body = await req.json()
        content = (body.get("content") or body.get("cookie_text") or "").strip()

    if not content or len(content) < 10:
        raise HTTPException(status_code=400, detail="Cookie content too short or invalid")

    if not is_netscape_format(content):
        content = convert_to_netscape(content)

    result = download_service.save_cookie(content)
    info = analyze_cookie(content)
    return {"ok": True, **result, **info}


@router.delete("")
async def delete_cookie():
    """删除 Cookie"""
    if Config.COOKIE_FILE.exists():
        Config.COOKIE_FILE.unlink()
    return {"ok": True}
