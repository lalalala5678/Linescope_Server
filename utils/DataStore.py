# utils/DataStore.py
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple
from zoneinfo import ZoneInfo

# 从同目录的 GetSensorData.py 引入数据生成函数
try:
    from .GetSensorData import generate_random_sample  # 包内相对导入
except Exception:
    from GetSensorData import generate_random_sample   # 脚本直跑兼容

# 从配置文件加载时间间隔设置
try:
    from config.settings import AppConfig
    _config = AppConfig()
    # 使用配置的传感器数据采集间隔
    INTERVAL = timedelta(minutes=_config.sensor_data_interval_minutes)
except ImportError:
    # 如果无法加载配置，使用默认值
    INTERVAL = timedelta(minutes=30)

# ------------------------
# 常量与路径
# ------------------------
DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_FILE = DATA_DIR / "data.txt"
TZ = ZoneInfo("Asia/Shanghai")

COLUMNS = [
    "timestamp_Beijing",
    "sway_speed_dps",
    "temperature_C",
    "humidity_RH",
    "pressure_hPa",
    "lux",
    "wire_foreign_object",
]

# ------------------------
# 小工具
# ------------------------
def _parse_ts(s: str) -> datetime:
    """解析 'YYYY-MM-DD HH:MM' 为带 Asia/Shanghai 时区的 datetime。"""
    return datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=TZ)

def _format_ts(dt: datetime) -> str:
    """格式化时间戳为 'YYYY-MM-DD HH:MM'。"""
    return dt.strftime("%Y-%m-%d %H:%M")

def _floor_to_half_hour(now: datetime) -> datetime:
    """向下取整到最近的半点（:00 或 :30），保留时区。"""
    minute = 0 if now.minute < 30 else 30
    return now.replace(minute=minute, second=0, microsecond=0)

def _read_all_lines() -> List[str]:
    """读取整个文件的所有行（保留换行），若不存在则报错明确提示。"""
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"未找到数据文件：{DATA_FILE}")
    return DATA_FILE.read_text(encoding="utf-8").splitlines()

def _write_all_lines(lines: List[str]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")

# ------------------------
# 函数 1：获取最新/最旧位置
# ------------------------
def get_positions() -> Tuple[int, int]:
    """
    无输入。
    返回 (latest_pos, oldest_pos) —— 二者均为**数据区内 0 基**索引：
      - oldest_pos 恒为 0（数据区第一行，即文件第 2 行）
      - latest_pos = 数据区最后一行的索引（= 行数 - 1）
    """
    lines = _read_all_lines()
    if not lines:
        raise ValueError("数据文件为空")

    # 检查表头
    header = lines[0].strip()
    if not header or "timestamp_Beijing" not in header:
        raise ValueError("数据文件缺少合法表头")

    data_count = len(lines) - 1  # 不含表头
    if data_count <= 0:
        raise ValueError("数据文件没有数据行")

    oldest_pos = 0
    latest_pos = data_count - 1
    return latest_pos, oldest_pos

# ------------------------
# 函数 2：计算需要插入多少条
# ------------------------
def compute_needed_inserts(pos: Tuple[int, int]) -> int:
    """
    输入：get_positions() 的返回值（(latest_pos, oldest_pos)）。
    读取最新一行的时间戳，与“当前北京时间向下取整到半点”的锚点比较，
    以 30 分钟为步长计算需要插入的条数。
      - 若最新时间戳 >= 当前半点，则返回 0。
      - 否则返回步数差（整数）。
    """
    lines = _read_all_lines()
    latest_pos, _ = pos

    # 最新数据行在文件中的实际行号 = latest_pos + 1（因为第 0 行是表头）
    latest_line = lines[latest_pos + 1].strip()
    latest_fields = latest_line.split(",")
    if len(latest_fields) < 1:
        raise ValueError("最新数据行解析失败")

    try:
        last_dt = _parse_ts(latest_fields[0])
    except Exception as e:
        raise ValueError(f"无法解析最新时间戳：{latest_fields[0]}") from e

    now_anchor = _floor_to_half_hour(datetime.now(TZ))

    if last_dt >= now_anchor:
        return 0

    diff = now_anchor - last_dt
    needed = int(diff.total_seconds() // INTERVAL.total_seconds())
    return max(0, needed)

# ------------------------
# （已剥离）函数 3：随机生成一组 —— 迁至 GetSensorData.py
# ------------------------
# def generate_random_sample() -> Tuple[float, float, float, float, float]: ...
# 现从 GetSensorData 导入，保持签名与返回值不变。

# ------------------------
# 函数 4：更新文件（滚动窗口）
# ------------------------
def update_data_file() -> int:
    """
    判断是否需要插入数据：
      - 若不需要，直接返回 0。
      - 若需要 N 条：
          1) 删去文件中**最老的 N 条**（表头后面的前 N 行）
          2) 在文件尾部**追加 N 条**，时间戳为“从最新时间戳起每 30 分钟补齐到当前半点”
    返回：本次插入的条数 N。
    """
    lines = _read_all_lines()
    header = lines[0].strip()
    if header.split(",") != COLUMNS:
        # 严格检查所有列顺序一致
        raise ValueError("表头与预期不一致，请检查列名顺序：\n" + ",".join(COLUMNS))

    latest_pos, oldest_pos = get_positions()
    needed = compute_needed_inserts((latest_pos, oldest_pos))
    if needed <= 0:
        return 0

    # 读取最新时间戳
    latest_fields = lines[latest_pos + 1].split(",")
    last_dt = _parse_ts(latest_fields[0])

    # 生成将要追加的 N 条行
    to_append: List[str] = []
    for i in range(1, needed + 1):
        ts = last_dt + i * INTERVAL
        ts_str = _format_ts(ts)
        sway, temp, hum, press, lux, wire_obj = generate_random_sample()
        to_append.append(f"{ts_str},{sway:.2f},{temp:.2f},{hum:.2f},{press:.2f},{lux:.2f},{wire_obj}")

    # 旧数据行（不含表头）
    data_lines = lines[1:]

    # 删除最老的 N 条；若现有数据少于 N，则清空
    if needed >= len(data_lines):
        kept = []
    else:
        kept = data_lines[needed:]

    new_lines = [header] + kept + to_append
    _write_all_lines(new_lines)
    return needed

# ------------------------
# main：自检
# ------------------------
def main():
    try:
        latest_pos, oldest_pos = get_positions()
        print(f"[INFO] latest_pos={latest_pos}, oldest_pos={oldest_pos}")

        need = compute_needed_inserts((latest_pos, oldest_pos))
        print(f"[INFO] needed_inserts={need}")

        inserted = update_data_file()
        if inserted > 0:
            print(f"[OK] 已插入 {inserted} 条新数据，并滚动删除同等数量的最老数据。")
        else:
            print("[OK] 当前无需插入数据。")
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    main()
