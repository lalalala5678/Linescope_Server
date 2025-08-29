# utils/GetSensorData.py
"""
传感器“随机数据”生成器（不含时间戳）。
保留 generate_random_sample(dt: Optional[datetime]) 接口不变。
- 若传入 dt：按昼夜规律生成。
- 若不传 dt：生成与时间无关的分布（与旧实现一致）。
时区策略：优先使用 ZoneInfo('Asia/Shanghai')；若系统缺 IANA tz（如 Windows 未装 tzdata），
则自动回退到固定东八区 timezone(timedelta(hours=8))，避免 ZoneInfoNotFoundError。
"""

from __future__ import annotations
from typing import Tuple, Optional
from datetime import datetime, timezone, timedelta
import random
import math

# ---- 时区工具：有 tzdata 用 ZoneInfo；否则退回固定 +08:00 ----
try:
    from zoneinfo import ZoneInfo  # Py3.9+
    def _get_bj_tz():
        try:
            return ZoneInfo("Asia/Shanghai")
        except Exception:
            return timezone(timedelta(hours=8))
except Exception:
    def _get_bj_tz():
        return timezone(timedelta(hours=8))

BJ_TZ = _get_bj_tz()


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _frac_day(dt: datetime) -> float:
    """当天的时间占比 [0,1)"""
    return (dt.hour * 60 + dt.minute) / (24 * 60)


def generate_random_sample(dt: Optional[datetime] = None) -> Tuple[float, float, float, float, float, int]:
    """
    生成一条随机数据（不含时间戳）：
        (sway_speed_dps, temperature_C, humidity_RH, pressure_hPa, lux, wire_foreign_object)

    参数：
        dt: 可选北京时间。若提供，则按昼夜节律生成更贴近真实的数值；
            不提供则使用与旧实现一致的时间无关分布。

    返回：
        六元组（5个float保留两位小数 + 1个int：0/1）
    """
    if dt is None:
        # —— 时间无关版本（保持与旧实现一致） ——
        gust = random.random() < 0.05
        sway = _clamp(random.uniform(5, 35) + (random.uniform(50, 200) if gust else 0.0), 0.0, 500.0)
        temperature = _clamp(random.gauss(22.0, 5.0), -25.0, 40.0)
        humidity = _clamp(random.gauss(60.0, 15.0), 5.0, 100.0)
        pressure = _clamp(random.gauss(1013.0, 6.0), 900.0, 1050.0)
        lux = _clamp(10_000.0 * (random.random() ** 3), 0.0, 10_000.0)
        
        # 异物检测：模拟低概率异物检测事件（约5%概率）
        wire_foreign_object = 1 if random.random() < 0.05 else 0
        
        return (round(sway, 2), round(temperature, 2), round(humidity, 2), round(pressure, 2), round(lux, 2), wire_foreign_object)

    # —— 时间相关版本：将 dt 转换/设定为北京时间 ----
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BJ_TZ)
    else:
        dt = dt.astimezone(BJ_TZ)

    f = _frac_day(dt)  # [0,1)
    hour = dt.hour + dt.minute / 60.0

    # 晃动速度：下午/傍晚略高 + 偶发阵风
    wind_proxy = 0.3 + 0.7 * abs(math.sin(2 * math.pi * (f - 0.15)))
    gust = random.random() < 0.05
    sway = 20 * wind_proxy + random.uniform(0, 15) + (random.uniform(50, 200) if gust else 0.0)
    sway = _clamp(sway, 0.0, 500.0)

    # 温度：昼夜正弦 + 噪声
    temperature = 20.0 + 8.0 * math.sin(2 * math.pi * (f - 0.25)) + random.gauss(0, 0.6)
    temperature = _clamp(temperature, -25.0, 40.0)

    # 湿度：与温度近似反相 + 噪声
    humidity = 65.0 - 10.0 * math.sin(2 * math.pi * (f - 0.25)) + random.gauss(0, 5.0)
    humidity = _clamp(humidity, 5.0, 100.0)

    # 气压：围绕 1013 的缓慢波动
    pressure = 1013.0 + 2.0 * math.sin(2 * math.pi * f) + random.gauss(0, 1.5)
    pressure = _clamp(pressure, 900.0, 1050.0)

    # 光照：白天 6:00–18:00 钟形，夜间 ~0
    if 6 <= hour <= 18:
        lux_base = math.sin(math.pi * (hour - 6) / 12.0)  # 0..1..0
        lux = 10_000.0 * (lux_base ** 1.5) + random.gauss(0, 80)
    else:
        lux = random.gauss(0, 2)
    lux = _clamp(lux, 0.0, 10_000.0)

    # 异物检测：时间相关逻辑 - 夜间和恶劣天气（高湿度/强风）时检测概率略高
    base_prob = 0.03  # 基础概率3%
    if not (6 <= hour <= 18):  # 夜间
        base_prob *= 1.5
    if humidity > 80:  # 高湿度
        base_prob *= 1.3
    if sway > 100:  # 强风晃动
        base_prob *= 2.0
    
    wire_foreign_object = 1 if random.random() < base_prob else 0

    return (round(sway, 2), round(temperature, 2), round(humidity, 2), round(pressure, 2), round(lux, 2), wire_foreign_object)


__all__ = ["generate_random_sample"]

if __name__ == "__main__":
    # 快速自测
    print("No-dt:", generate_random_sample())
    from datetime import datetime
    print("With now:", generate_random_sample(datetime.now()))
