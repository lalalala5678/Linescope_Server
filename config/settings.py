import os
import logging
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@dataclass(frozen=True)
class AppConfig:
    """应用运行期配置（可扩展为从环境变量或文件加载）"""
    datastore_interval_minutes: int = 30
    stream_frame_interval_sec: float = 0.2  # 约 5 FPS（按需调整）
    log_file: str = os.path.join(PROJECT_ROOT, "app.log")
    log_max_bytes: int = 5 * 1024 * 1024  # 5MB
    log_backup_count: int = 3


def configure_logging(cfg: AppConfig) -> None:
    """配置应用日志"""
    os.makedirs(os.path.dirname(cfg.log_file), exist_ok=True)
    handler = RotatingFileHandler(
        cfg.log_file, maxBytes=cfg.log_max_bytes, backupCount=cfg.log_backup_count, encoding="utf-8"
    )
    fmt = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(name)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(fmt)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    # 同时把 INFO 以上日志打到控制台，便于开发
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)