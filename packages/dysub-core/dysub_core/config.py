"""DySub configuration loaded from environment and .env files."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

CONFIG_DIR = Path.home() / ".config" / "dysub"
DEFAULT_ENV_PATH = CONFIG_DIR / ".env"

ENV_TEMPLATE = """# DySub 配置文件
# 使用方法：
#   1. 复制此文件到 ~/.config/dysub/.env（推荐，全局生效）
#   2. 或复制到项目根目录的 .env（仅当前目录生效）
#   3. 填入你的真实 API Key

# ================================================
# 必填：ASR API Key
# ================================================
# 支持 OpenAI Whisper、阿里云、讯飞等兼容 OpenAI 接口的服务商
# 获取方式： https://bailian.console.aliyun.com/
DYSUB_ASR_API_KEY=sk-your-api-key-here

# ================================================
# 可选：自定义 ASR 接口地址
# ================================================
# 使用阿里百炼时填写：
DYSUB_ASR_BASE_URL=https://dashscope.aliyuncs.com/api/v1

# 使用 OpenAI 官方时留空即可
# DYSUB_ASR_BASE_URL=https://api.openai.com/v1

# ================================================
# 可选：默认语言
# ================================================
# DYSUB_DEFAULT_LANGUAGE=zh

# ================================================
# 可选：默认输出格式
# ================================================
# DYSUB_DEFAULT_FORMAT=srt
"""


class Settings(BaseSettings):
    """Global DySub settings.

    Reads from (in precedence order):
    1. Environment variables (prefix: DYSUB_)
    2. ~/.config/dysub/.env
    3. ./.env (current working directory)
    """

    model_config = SettingsConfigDict(
        env_prefix="DYSUB_",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    asr_api_key: str = ""
    asr_base_url: str | None = None
    default_language: str = "zh"
    default_format: str = "srt"

    @classmethod
    def load(cls) -> Settings:
        """Load settings, checking multiple .env file locations."""
        env_files = [
            str(DEFAULT_ENV_PATH),
            ".env",
        ]
        # Filter to existing files so pydantic-settings doesn't warn
        existing = [f for f in env_files if Path(f).exists()]
        return cls(_env_file=existing or None)


def ensure_config_dir() -> Path:
    """Create ~/.config/dysub/ if it doesn't exist."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR
