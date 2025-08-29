import os
import logging
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@dataclass(frozen=True)
class AppConfig:
    """应用运行期配置（可扩展为从环境变量或文件加载）"""
    # 原有配置
    datastore_interval_minutes: int = 30
    stream_frame_interval_sec: float = 0.2  # 约 5 FPS（按需调整）
    
    # 数据采集时间间隔配置
    sensor_data_interval_minutes: int = 30  # 传感器数据采集间隔（分钟）
    foreign_object_check_interval_sec: float = 0.2  # 异物检测间隔（秒）
    log_file: str = os.path.join(PROJECT_ROOT, "app.log")
    log_max_bytes: int = 5 * 1024 * 1024  # 5MB
    log_backup_count: int = 3
    
    # 数据源配置
    data_source_type: str = "file"  # "file" | "sql"
    data_file_path: str = os.path.join("utils", "data", "data.txt")  # 相对于PROJECT_ROOT
    
    # 缓存配置
    cache_enabled: bool = True
    cache_ttl: int = 1800  # 30分钟缓存TTL（秒）
    cache_key_prefix: str = "linescope"
    
    # Redis配置
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""  # 空字符串表示无密码
    
    # SQL数据库配置（预留，未来使用）
    db_connection_string: str = ""
    db_table_name: str = "sensor_data"
    db_pool_size: int = 10


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