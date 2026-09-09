"""
配置管理模块
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Config:
    """全局配置"""

    # API Keys（仅从环境变量读取，不内置明文；本地由 backend/.env 提供，
    # Docker 由 compose 的 env_file 注入。缺失时启动可运行但调用 LLM 会报 401）
    SILICONFLOW_API_KEY: str | None = os.getenv("SILICONFLOW_API_KEY")

    # LLM Config
    LLM_BASE_URL: str = "https://api.siliconflow.cn/v1"
    LLM_MODEL: str = "deepseek-ai/DeepSeek-V4-Pro"
    EMBEDDING_MODEL: str = "BAAI/bge-large-zh-v1.5"

    # Path Config
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DOWNLOAD_DIR: Path = BASE_DIR / "downloads"
    COOKIE_FILE: Path = BASE_DIR / "cookie.txt"
    # 共享目录：宿主机与容器双向可见，用户把外部文件放这里供 Agent 读取
    COOKIE_IMPORT_DIR: Path = BASE_DIR / "cookie_imports"   # cookie 专用导入目录
    SHARED_DIR: Path = BASE_DIR / "shared"                  # 通用共享目录（任意文件）

    # Agent 可读目录白名单：key 是工具参数用的目录名，value 是对应路径。
    # 安全边界：read_file 等工具只能读这里的目录，不能读 backend 代码/.env 等。
    # 未来想开放更多目录给 Agent：在此登记 + docker-compose.yml 加挂载即可。
    READABLE_DIRS: dict[str, Path] = {
        "cookie_imports": COOKIE_IMPORT_DIR,
        "shared": SHARED_DIR,
        "downloads": DOWNLOAD_DIR,
    }

    # Server Config
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Download Config
    MAX_CONCURRENT_DOWNLOADS: int = 3

    @classmethod
    def ensure_dirs(cls):
        """确保必要目录存在"""
        cls.DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        cls.COOKIE_IMPORT_DIR.mkdir(parents=True, exist_ok=True)
        cls.SHARED_DIR.mkdir(parents=True, exist_ok=True)


Config.ensure_dirs()
