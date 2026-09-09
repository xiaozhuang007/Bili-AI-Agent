"""
Agent 工具模块
将下载服务封装为 LangChain Tool，供 Agent 调用
"""

from pathlib import Path

from langchain_core.tools import tool

from config import Config
from services.download_service import download_service
from services.utils import extract_bilibili_url
from services.cookie_utils import (
    is_netscape_format,
    convert_to_netscape,
    analyze_cookie,
    convert_cookie_content,
    detect_cookie_format,
    verify_cookie_login,
)


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


@tool
def read_file(filename: str, directory: str = "cookie_imports") -> str:
    """Read a text file from an allowed shared directory.
    Input: filename (plain name only, no path), and directory (cookie_imports | shared | downloads).
    Returns the file content, or an error message if the file is not accessible."""
    # 安全边界1：只允许纯文件名，拒绝一切路径分隔符/上级目录符号。
    # 为什么：Agent 跑在容器内，路径穿越（如 ../backend/.env）可读到敏感文件；
    # 共享目录的设计就是“平铺放文件”，用户把文件丢进目录后用名字引用即可。
    if Path(filename).name != filename:
        return "Error: filename must be a plain name (no / or \\ or ..). Put the file into the shared directory first."

    # 安全边界2：目录必须是白名单里的 key（config.Config.READABLE_DIRS），
    # 防止读到 backend 代码/.env 等未授权位置。
    if directory not in Config.READABLE_DIRS:
        allowed = ", ".join(Config.READABLE_DIRS.keys())
        return f"Error: directory must be one of: {allowed}"

    file_path = Config.READABLE_DIRS[directory] / filename
    if not file_path.is_file():
        return f"Error: File '{filename}' not found in directory '{directory}' (searched: {file_path})."

    # 编码兼容：优先 utf-8（浏览器扩展导出常用），失败退回 latin-1 兜底，
    # 避免个别非 utf-8 文件导致读不出来。
    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = file_path.read_text(encoding="latin-1")

    return content


@tool
def check_cookie_file(filename: str) -> str:
    """Check whether a Cookie file in the cookie_imports directory is usable.
    Input: filename (e.g. 'cookies.txt').
    Runs format detection, key-field analysis, expiration check, and a REAL login test
    against Bilibili API. Returns a full usability report."""
    content = read_file.invoke({"filename": filename, "directory": "cookie_imports"})
    if content.startswith("Error:"):
        return content

    content = content.strip()
    if not content:
        return "Error: The file is empty."

    fmt = detect_cookie_format(content)

    # 非 Netscape 也能检测字段/实测：先统一转 Netscape，检测逻辑只需处理一种格式
    ok, netscape_text, _ = convert_cookie_content(content)
    if not ok:
        return f"Error: {netscape_text}"

    info = analyze_cookie(netscape_text)
    login = verify_cookie_login(netscape_text)

    fields = info["fields_status"]
    missing = [k for k, v in fields.items() if not v]

    lines = [
        f"Cookie file: {filename}",
        f"Format: {fmt} (Netscape-compatible: yes)",
        f"Cookie entries: {info['cookie_count']}",
    ]

    # 关键字段完整性报告
    lines.append(f"Key fields: {', '.join(k + (' OK' if v else ' MISSING') for k, v in fields.items())}")
    if missing:
        lines.append(f"Warning: Missing fields -> {', '.join(missing)}")

    # 过期时间报告
    if info["expiration"]:
        lines.append(f"Expires: {info['expiration']} (days left: {info['days_left']})")
        if info["days_left"] == 0:
            lines.append("Warning: Cookie has EXPIRED!")

    # 实测登录态（最有说服力的可用性证据）
    if login["isLogin"]:
        lines.append(f"Login test: PASSED (user: {login['uname']}, uid: {login['mid']})")
        lines.append("Verdict: Cookie is usable.")
    else:
        lines.append(f"Login test: FAILED - {login['detail']}")
        lines.append("Verdict: Cookie is NOT usable. Ask the user to re-export it.")

    return "\n".join(lines)


@tool
def convert_cookie_file(filename: str) -> str:
    """Convert a Cookie file in cookie_imports to Netscape format and make it active.
    Input: filename (e.g. 'cookies.json' or 'cookies.txt').
    The original file is NEVER modified. The converted result is saved BOTH as a
    '_netscape.txt' copy next to the original AND applied as the current active Cookie.
    Returns conversion + verification report."""
    content = read_file.invoke({"filename": filename, "directory": "cookie_imports"})
    if content.startswith("Error:"):
        return content

    content = content.strip()
    if not content:
        return "Error: The file is empty."

    fmt = detect_cookie_format(content)
    ok, netscape_text, _ = convert_cookie_content(content)
    if not ok:
        return f"Error: {netscape_text}"

    # 已经是 Netscape：无需转换，但也确认一下是否要应用为生效 cookie（幂等，无副作用）
    if fmt == "netscape":
        lines = [f"Format: Netscape already - no conversion needed."]
    else:
        # 写一份转换产物副本到 cookie_imports/，文件名 = 原名 + _netscape 后缀。
        # 为什么保留副本：用户可自行取用/给其他项目；原始文件保持不动。
        src = Path(filename)
        out_name = f"{src.stem}_netscape.txt"
        out_path = Config.COOKIE_IMPORT_DIR / out_name
        out_path.write_text(netscape_text, encoding="utf-8")
        lines = [f"Converted: {fmt} -> Netscape. Copy saved as: cookie_imports/{out_name}"]

    # 方案C：同时应用为当前生效 Cookie（yt-dlp 下载直接使用）
    result = download_service.save_cookie(netscape_text)
    lines.append(f"Applied as active Cookie: {result['size']} bytes written to cookie.txt")

    # 转换后验证：字段分析 + 实测登录态
    info = analyze_cookie(netscape_text)
    login = verify_cookie_login(netscape_text)
    lines.append(f"Cookie entries: {info['cookie_count']}")
    fields = info["fields_status"]
    lines.append(f"Key fields: {', '.join(k + (' OK' if v else ' MISSING') for k, v in fields.items())}")

    if login["isLogin"]:
        lines.append(f"Login test: PASSED (user: {login['uname']}, uid: {login['mid']})")
        lines.append("Verdict: Cookie converted and verified usable.")
    else:
        lines.append(f"Login test: FAILED - {login['detail']}")
        lines.append("Warning: Converted but login test failed - the Cookie itself may be expired or revoked.")

    return "\n".join(lines)


# 所有工具列表
ALL_TOOLS = [
    download_video,
    get_download_status,
    list_downloads,
    get_video_info,
    check_cookie_status,
    update_cookie,
    read_file,
    check_cookie_file,
    convert_cookie_file,
    list_all_tasks,
]
