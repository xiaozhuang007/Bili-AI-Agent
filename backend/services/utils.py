"""
通用工具函数模块
从 bilibili-web-downloader 迁移，保持核心逻辑不变
"""

import os
import re
import socket
from pathlib import Path
from urllib.parse import urlparse

from services.cookie_utils import is_netscape_format, convert_to_netscape


def get_local_ip() -> str:
    """获取本机局域网 IP"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def is_bilibili_url(url: str) -> bool:
    """验证是否为有效的 B站 URL"""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        return False
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return False
    return "bilibili.com" in host or "b23.tv" in host


def extract_bilibili_url(text: str) -> str | None:
    """从任意文本中提取第一个 B站 URL"""
    text = text.strip()
    if is_bilibili_url(text):
        return text

    patterns = [
        r'https?://b23\.tv/[a-zA-Z0-9]+',
        r'https?://www\.bilibili\.com/video/[a-zA-Z0-9]+',
        r'https?://bilibili\.com/video/[a-zA-Z0-9]+',
        r'https?://m\.bilibili\.com/video/[a-zA-Z0-9]+',
        r'https?://www\.bilibili\.com//video/[a-zA-Z0-9]+',
        r'https?://bilibili\.com//video/[a-zA-Z0-9]+',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(0)
    return None


def safe_name(name: str) -> str:
    """清理文件名中的非法字符"""
    return re.sub(r'[\\/:*?"<>|\n\r\t]', "_", name).strip()[:100]


def get_cookie_path(cookie_file: Path) -> str | None:
    """获取可用的 cookie 文件路径。

    若文件存在但非 Netscape 格式（如浏览器字符串格式
    ``name=value; name2=value2; ...``），自动转换为 yt-dlp 所需的
    Netscape HTTP Cookie File 格式并写回原文件，使后续读取直接生效。
    """
    if not (cookie_file.exists() and cookie_file.stat().st_size > 0):
        return None

    try:
        content = cookie_file.read_text(encoding="utf-8").strip()
    except UnicodeDecodeError:
        content = cookie_file.read_text(encoding="latin-1").strip()

    if content and not is_netscape_format(content):
        converted = convert_to_netscape(content)
        cookie_file.write_text(converted, encoding="utf-8")
        print(f"[Cookie] 检测到非 Netscape 格式，已自动转换为 Netscape 格式并写回: {cookie_file}")

    return str(cookie_file)
