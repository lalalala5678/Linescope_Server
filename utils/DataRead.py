# DataRead.py
# 读取同目录下 data/data.txt，并返回解析结果。
# 若直接运行本文件，则打印读取结果到控制台。

from __future__ import annotations
import csv
from pathlib import Path
from typing import List, Dict, Any

# 期望的列名（与生成脚本保持一致）
_EXPECTED_COLUMNS = [
    "timestamp_Beijing",
    "sway_speed_dps",
    "temperature_C",
    "humidity_RH",
    "pressure_hPa",
    "lux",
]

def read_sensor_data(file_path: str | None = None) -> List[Dict[str, Any]]:
    """
    读取与 DataRead.py 同一文件夹下 data/data.txt（或传入的 file_path）中的内容，
    返回列表[dict]，字段如下：
        - timestamp_Beijing: str  (例: '2025-08-18 23:30')
        - sway_speed_dps:   float
        - temperature_C:    float
        - humidity_RH:      float
        - pressure_hPa:     float
        - lux:              float
    """
    # 默认路径：<当前文件所在目录>/data/data.txt
    if file_path is None:
        file_path = str(Path(__file__).resolve().parent / "data" / "data.txt")

    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(
            f"未找到数据文件：{p}\n"
            "请确认 DataRead.py 同目录下存在 data/data.txt，或传入正确的 file_path。"
        )

    rows: List[Dict[str, Any]] = []
    with p.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        # 简单字段校验
        if reader.fieldnames is None:
            raise ValueError("无法读取表头，请检查文件内容是否为 CSV 并包含表头行。")
        missing = [c for c in _EXPECTED_COLUMNS if c not in reader.fieldnames]
        if missing:
            raise ValueError(f"表头缺失字段：{missing}，请检查文件格式是否正确。")

        for row in reader:
            # 类型转换：保留时间戳为 str，其余转换为 float
            try:
                parsed = {
                    "timestamp_Beijing": row["timestamp_Beijing"],
                    "sway_speed_dps": float(row["sway_speed_dps"]),
                    "temperature_C":   float(row["temperature_C"]),
                    "humidity_RH":     float(row["humidity_RH"]),
                    "pressure_hPa":    float(row["pressure_hPa"]),
                    "lux":             float(row["lux"]),
                }
            except (KeyError, ValueError) as e:
                raise ValueError(f"解析行失败：{row}\n错误：{e}")
            rows.append(parsed)

    return rows


if __name__ == "__main__":
    # 直接运行则打印读取结果
    data = read_sensor_data()
    # 直接打印列表（672 行会较长，如需只看前几行可自行切片）
    from pprint import pprint
    pprint(data)
