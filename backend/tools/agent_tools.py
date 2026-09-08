"""
Agent 工具模块
将下载服务封装为 LangChain Tool，供 Agent 调用
"""

from langchain_core.tools import tool

from config import Config
from services.download_service import download_service
from services.utils import extract_bilibili_url
from services.cookie_utils import is_netscape_format, convert_to_netscape, analyze_cookie


@tool
def download_video(url: str) -> str:
    """Download a Bilibili video. Input: a Bilibili video URL or text containing a URL.
    Returns download task status."""
    video_url = extract_bilibili_url(url)
    if not video_url:
        return f"Error: No valid Bilibili URL found in: {url}"

    info = download_service.get_video_info(video_url)
    if not info:
        return f"Error: Cannot get video info. The URL may be invalid or Cookie is expired."

    task_id = download_service.start_download(video_url, info['title'])
    return (
        f"Download started! Task ID: {task_id}\n"
        f"Title: {info['title']}\n"
        f"Uploader: {info['uploader']}\n"
        f"Duration: {info['duration']}s\n"
        f"Use get_download_status with task_id '{task_id}' to check progress."
    )


@tool
def get_download_status(task_id: str) -> str:
    """Check the download progress of a task. Input: task_id string.
    Returns current status, progress percentage, speed, and ETA."""
    task = download_service.get_status(task_id)
    if not task:
        return f"Error: Task '{task_id}' not found."

    status = task["status"]
    if status == "done":
        return (
            f"Download complete!\n"
            f"File: {task['filename']}\n"
            f"Size: {task['filesize_mb']} MB"
        )
    elif status == "error":
        return f"Download failed: {task['error']}"
    elif status == "downloading":
        return (
            f"Downloading... {task['progress']}%\n"
            f"Speed: {task['speed']}\n"
            f"ETA: {task['eta']}"
        )
    else:
        return f"Status: {status}, Progress: {task['progress']}%"


@tool
def list_downloads() -> str:
    """List all downloaded video files. No input needed.
    Returns a list of downloaded files with name, size, and download time."""
    files = download_service.list_downloads()
    if not files:
        return "No downloaded files yet."

    lines = [f"Total {len(files)} files:\n"]
    for i, f in enumerate(files[:20], 1):
        lines.append(f"{i}. {f['name']} ({f['size_mb']} MB, {f['time']})")

    if len(files) > 20:
        lines.append(f"\n... and {len(files) - 20} more files")

    return "\n".join(lines)


@tool
def get_video_info(url: str) -> str:
    """Get video information without downloading. Input: a Bilibili video URL.
    Returns title, uploader, duration, and view count."""
    video_url = extract_bilibili_url(url)
    if not video_url:
        return f"Error: No valid Bilibili URL found in: {url}"

    info = download_service.get_video_info(video_url)
    if not info:
        return "Error: Cannot get video info. Check URL or Cookie status."

    duration_min = info['duration'] // 60 if info['duration'] else 0
    duration_sec = info['duration'] % 60 if info['duration'] else 0

    return (
        f"Title: {info['title']}\n"
        f"Uploader: {info['uploader']}\n"
        f"Duration: {duration_min}m{duration_sec}s\n"
        f"Views: {info['view_count']:,}"
    )


@tool
def check_cookie_status() -> str:
    """Check the current Cookie status. No input needed.
    Returns whether Cookie exists, key fields status, and expiration info."""
    status = download_service.get_cookie_status()

    if not status.get("has_cookie"):
        return "Warning: No Cookie set. Some videos may not be downloadable. Please upload Cookie."

    result = f"Cookie exists ({status.get('cookie_count', 0)} entries)\n"

    fields = status.get("fields_status", {})
    missing = [k for k, v in fields.items() if not v]
    present = [k for k, v in fields.items() if v]

    if present:
        result += f"Present fields: {', '.join(present)}\n"
    if missing:
        result += f"Warning: Missing fields: {', '.join(missing)}\n"

    if status.get("expiration"):
        result += f"Expires: {status['expiration']}\n"
        if status.get("days_left") is not None:
            if status["days_left"] == 0:
                result += "Warning: Cookie has expired!\n"
            else:
                result += f"Days left: {status['days_left']}\n"

    return result


@tool
def update_cookie(cookie_content: str) -> str:
    """Update the Cookie file. Input: Cookie content string (Netscape format or browser string format).
    Returns the save result and Cookie analysis."""
    content = cookie_content.strip()
    if not content or len(content) < 10:
        return "Error: Cookie content is too short or invalid."

    if not is_netscape_format(content):
        content = convert_to_netscape(content)

    result = download_service.save_cookie(content)
    info = analyze_cookie(content)

    return (
        f"Cookie saved successfully! ({result['size']} bytes)\n"
        f"Cookie entries: {info['cookie_count']}\n"
        f"SESSDATA: {'OK' if info['fields_status'].get('SESSDATA') else 'MISSING'}\n"
        f"DedeUserID: {'OK' if info['fields_status'].get('DedeUserID') else 'MISSING'}"
    )


@tool
def list_all_tasks() -> str:
    """List all download tasks (including pending, downloading, done, and failed).
    No input needed. Returns task list with status."""
    tasks = download_service.list_tasks()
    if not tasks:
        return "No download tasks yet."

    lines = [f"Total {len(tasks)} tasks:\n"]
    for i, t in enumerate(tasks[:20], 1):
        status_emoji = {
            "done": "[DONE]",
            "downloading": "[DL]",
            "error": "[ERR]",
            "pending": "[WAIT]",
        }.get(t["status"], t["status"])

        line = f"{i}. {status_emoji} {t.get('video_label', t.get('title', 'unknown'))[:30]}"
        if t["status"] == "downloading":
            line += f" - {t['progress']}%"
        elif t["status"] == "done":
            line += f" - {t.get('filesize_mb', 0)} MB"
        elif t["status"] == "error":
            line += f" - {t.get('error', '')[:30]}"

        lines.append(line)

    return "\n".join(lines)


# 所有工具列表
ALL_TOOLS = [
    download_video,
    get_download_status,
    list_downloads,
    get_video_info,
    check_cookie_status,
    update_cookie,
    list_all_tasks,
]
