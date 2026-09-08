"""
下载服务模块
复用原项目核心下载逻辑，封装为可被 Agent 调用的服务
"""

import uuid
import threading
from pathlib import Path
from datetime import datetime

import yt_dlp

from config import Config
from services.utils import safe_name, get_cookie_path
from services.cookie_utils import analyze_cookie


class DownloadService:
    """下载服务，管理下载任务"""

    def __init__(self):
        self.tasks: dict = {}
        self.tasks_lock = threading.Lock()

    def get_video_info(self, url: str) -> dict | None:
        """获取视频信息（不下载）"""
        cookie_path = get_cookie_path(Config.COOKIE_FILE)

        ydl_opts = {'skip_download': True, 'noplaylist': True}
        if cookie_path:
            ydl_opts['cookiefile'] = cookie_path

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info:
                    return {
                        'title': info.get('title', ''),
                        'uploader': info.get('uploader', ''),
                        'duration': info.get('duration', 0),
                        'view_count': info.get('view_count', 0),
                        'url': url,
                    }
        except Exception as e:
            print(f"[DownloadService] get_video_info error: {e}")
        return None

    def start_download(self, url: str, title: str = None) -> str:
        """启动下载任务，返回 task_id"""
        if not title:
            info = self.get_video_info(url)
            title = info['title'] if info else f"bilibili_{uuid.uuid4().hex[:8]}"

        task_id = uuid.uuid4().hex[:8]

        with self.tasks_lock:
            self.tasks[task_id] = {
                "status": "pending",
                "progress": 0,
                "title": title,
                "video_label": title[:40],
                "filename": None,
                "filesize_mb": 0,
                "speed": "",
                "eta": "",
                "error": None,
                "created_at": datetime.now().isoformat(),
            }

        t = threading.Thread(
            target=self._download_worker,
            args=(task_id, url, title),
            daemon=True
        )
        t.start()

        return task_id

    def _download_worker(self, task_id: str, video_url: str, title: str):
        """后台下载线程"""
        with self.tasks_lock:
            self.tasks[task_id]["status"] = "downloading"
            self.tasks[task_id]["progress"] = 0

        cookie_path = get_cookie_path(Config.COOKIE_FILE)
        filename_base = safe_name(title) or f"bilibili_{uuid.uuid4().hex[:8]}"
        out_tpl = str(Config.DOWNLOAD_DIR / f"{filename_base}.%(ext)s")

        def progress_hook(d: dict):
            if d['status'] == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate') or d.get('fragment_count')
                downloaded = d.get('downloaded_bytes') or 0
                speed = d.get('speed') or 0
                eta = d.get('eta') or 0

                if total and total > 0:
                    pct = min(int(downloaded / total * 100), 99)
                else:
                    pct = 0

                if speed > 1024 * 1024:
                    speed_str = f"{speed / 1024 / 1024:.1f} MB/s"
                elif speed > 1024:
                    speed_str = f"{speed / 1024:.1f} KB/s"
                else:
                    speed_str = f"{speed:.0f} B/s"

                if eta > 60:
                    eta_str = f"{int(eta // 60)}m{int(eta % 60)}s"
                else:
                    eta_str = f"{int(eta)}s"

                with self.tasks_lock:
                    self.tasks[task_id]["progress"] = pct
                    self.tasks[task_id]["speed"] = speed_str
                    self.tasks[task_id]["eta"] = eta_str

            elif d['status'] == 'finished':
                with self.tasks_lock:
                    self.tasks[task_id]["progress"] = 99

        try:
            ydl_opts = {
                'noplaylist': True,
                'nocheckcertificate': True,
                'retries': 3,
                'socket_timeout': 60,
                'outtmpl': out_tpl,
                'format': 'bestvideo+bestaudio/best',
                'merge_output_format': 'mp4',
                'progress_hooks': [progress_hook],
            }

            if cookie_path:
                ydl_opts['cookiefile'] = cookie_path

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])

            # 查找下载结果文件
            result_file = self._find_result_file(filename_base)

            if result_file and result_file.exists():
                size_mb = round(result_file.stat().st_size / 1048576, 2)

                with self.tasks_lock:
                    self.tasks[task_id]["status"] = "done"
                    self.tasks[task_id]["progress"] = 100
                    self.tasks[task_id]["filename"] = result_file.name
                    self.tasks[task_id]["filesize_mb"] = size_mb

                print(f"[OK] {result_file.name} ({size_mb:.1f} MB)")
            else:
                raise Exception("No video file found after download")

        except Exception as e:
            with self.tasks_lock:
                self.tasks[task_id]["status"] = "error"
                self.tasks[task_id]["error"] = str(e)
            print(f"[ERR] {e}")

    def _find_result_file(self, filename_base: str) -> Path | None:
        """查找下载结果文件"""
        video_exts = {".mp4", ".webm", ".mkv", ".flv"}

        # 策略1: glob 匹配
        candidates = sorted(
            Config.DOWNLOAD_DIR.glob(f"{filename_base}.*"),
            key=lambda f: f.stat().st_mtime,
        )
        video_files = [f for f in candidates if f.suffix.lower() in video_exts]
        if video_files:
            return video_files[-1]

        # 策略2: 找最新的视频文件
        all_videos = sorted(
            [f for f in Config.DOWNLOAD_DIR.iterdir() if f.is_file() and f.suffix.lower() in video_exts],
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )
        return all_videos[0] if all_videos else None

    def get_status(self, task_id: str) -> dict | None:
        """获取任务状态"""
        with self.tasks_lock:
            return self.tasks.get(task_id)

    def list_downloads(self) -> list:
        """列出已下载文件"""
        files = []
        if not Config.DOWNLOAD_DIR.exists():
            return files

        for f in Config.DOWNLOAD_DIR.iterdir():
            if f.is_file() and f.suffix.lower() in {".mp4", ".webm", ".mkv", ".flv"}:
                stat = f.stat()
                files.append({
                    "name": f.name,
                    "size_mb": round(stat.st_size / 1048576, 2),
                    "time": datetime.fromtimestamp(stat.mtime).strftime("%m-%d %H:%M"),
                })

        files.sort(key=lambda x: x["time"], reverse=True)
        return files

    def list_tasks(self) -> list:
        """列出所有下载任务"""
        with self.tasks_lock:
            return list(self.tasks.values())

    def get_cookie_status(self) -> dict:
        """获取 Cookie 状态（若为非 Netscape 格式会自动转换归一化）"""
        cookie_path = get_cookie_path(Config.COOKIE_FILE)
        if cookie_path:
            cookie_file = Path(cookie_path)
            try:
                content = cookie_file.read_text(encoding='utf-8').strip()
                info = analyze_cookie(content)
                return {
                    "has_cookie": True,
                    "size": len(content),
                    **info,
                }
            except Exception:
                return {"has_cookie": True, "size": cookie_file.stat().st_size}
        return {"has_cookie": False, "size": 0}

    def save_cookie(self, content: str) -> dict:
        """保存 Cookie"""
        Config.COOKIE_FILE.write_text(content, encoding='utf-8')
        return {"ok": True, "size": len(content)}


# 全局单例
download_service = DownloadService()
