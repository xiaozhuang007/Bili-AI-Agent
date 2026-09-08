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

    # Server Config
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Download Config
    MAX_CONCURRENT_DOWNLOADS: int = 3

    @classmethod
    def ensure_dirs(cls):
        """确保必要目录存在"""
        cls.DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


Config.ensure_dirs()
