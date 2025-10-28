"""I1 传感器数据内存存储。"""
from __future__ import annotations

import threading
import logging
import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Deque, Dict, List, Optional, Tuple

try:
    from zoneinfo import ZoneInfo  # type: ignore
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore

if ZoneInfo is not None:
    BJ_TZ = ZoneInfo("Asia/Shanghai")
else:  # Windows 未安装 tzdata 时退化为固定偏移
    BJ_TZ = timezone(timedelta(hours=8))


@dataclass(frozen=True)
class StoredRecord:
    timestamp_str: str
    sway_speed_dps: float
    temperature_c: float
    humidity_rh: float
    pressure_hpa: float
    lux: float
    wire_foreign_object: int
    component_id: str
    frame_no: int
    wind_speed_avg_10min: float
    wind_direction_deg: float
    wind_speed_max: float
    wind_speed_extreme: float
    precipitation_mm: float
    precipitation_intensity_mm_min: float
    raw_payload: object


class I1DataStore:
    """在内存中缓存 I1 解析后的结构化数据。"""

    def __init__(
        self,
        max_records: int = 288,
        line_temp_alert_threshold: float = 80.0,
        line_temp_alert_timeout: int = 600,
    ) -> None:
        self._max_records = max(1, max_records)
        self._line_temp_alert_threshold = line_temp_alert_threshold
        self._line_temp_alert_timeout = max(1, line_temp_alert_timeout)

        self._weather_records: Deque[StoredRecord] = deque(maxlen=self._max_records)
        self._line_temp_alerts: Dict[str, Tuple[float, bool]] = {}
        self._logger = logging.getLogger(__name__)
        self._latest_tower_tilt: Dict[str, object] = {}
        self._latest_heartbeat: Optional[object] = None

        self._lock = threading.RLock()
        self._update_counter = 0
        self._last_update_counter_checked = 0

    # ----------------------------
    # 配置调整
    # ----------------------------
    def configure(
        self,
        *,
        max_records: Optional[int] = None,
        line_temp_alert_threshold: Optional[float] = None,
        line_temp_alert_timeout: Optional[int] = None,
    ) -> None:
        with self._lock:
            if max_records is not None and max_records != self._max_records:
                max_records = max(1, max_records)
                self._max_records = max_records
                self._weather_records = deque(self._weather_records, maxlen=max_records)
            if line_temp_alert_threshold is not None:
                self._line_temp_alert_threshold = line_temp_alert_threshold
            if line_temp_alert_timeout is not None:
                self._line_temp_alert_timeout = max(1, line_temp_alert_timeout)

    # ----------------------------
    # 数据写入
    # ----------------------------
    def add_weather(self, payload, frame_no: int) -> StoredRecord:
        record = StoredRecord(
            timestamp_str=self._format_timestamp(payload.time_stamp),
            sway_speed_dps=round(payload.standard_wind_speed, 2),
            temperature_c=round(payload.air_temperature, 2),
            humidity_rh=round(payload.humidity, 2),
            pressure_hpa=round(payload.air_pressure, 2),
            lux=round(float(payload.radiation_intensity), 2),
            wire_foreign_object=self._get_wire_flag(payload.component_id, payload.time_stamp),
            component_id=payload.component_id,
            frame_no=frame_no,
            wind_speed_avg_10min=round(payload.average_wind_speed, 2),
            wind_direction_deg=float(payload.average_wind_direction),
            wind_speed_max=round(payload.max_wind_speed, 2),
            wind_speed_extreme=round(payload.extreme_wind_speed, 2),
            precipitation_mm=round(payload.precipitation, 2),
            precipitation_intensity_mm_min=round(payload.precipitation_intensity, 2),
            raw_payload=payload,
        )
        with self._lock:
            self._weather_records.append(record)
            self._update_counter += 1
            self._logger.info("Weather record stored: %s (total=%s)", record, len(self._weather_records))
        return record

    def add_line_temperature(self, payload) -> None:
        is_alert = payload.line_temperature >= self._line_temp_alert_threshold
        event_ts = float(payload.time_stamp)
        with self._lock:
            self._line_temp_alerts[payload.component_id] = (event_ts, is_alert)
            self._update_counter += 1
            self._logger.debug("Line temperature stored: %s", payload)

    def add_tower_tilt(self, payload) -> None:
        with self._lock:
            self._latest_tower_tilt[payload.component_id] = payload
            self._update_counter += 1

    def add_heartbeat(self, payload) -> None:
        with self._lock:
            self._latest_heartbeat = payload
            self._update_counter += 1

    # ----------------------------
    # 数据读取
    # ----------------------------
    def get_all_weather(self) -> List[Dict[str, object]]:
        with self._lock:
            return [self._record_to_dict(rec) for rec in list(self._weather_records)]

    def get_latest_weather(self) -> Optional[Dict[str, object]]:
        with self._lock:
            if not self._weather_records:
                return None
            return self._record_to_dict(self._weather_records[-1])

    def get_recent_weather(self, limit: int) -> List[Dict[str, object]]:
        if limit <= 0:
            return self.get_all_weather()
        with self._lock:
            slice_records = list(self._weather_records)[-limit:]
            return [self._record_to_dict(rec) for rec in slice_records]

    def get_weather_count(self) -> int:
        with self._lock:
            return len(self._weather_records)

    def get_latest_tower_tilt(self) -> Dict[str, object]:
        with self._lock:
            return dict(self._latest_tower_tilt)

    def get_latest_heartbeat(self) -> Optional[object]:
        with self._lock:
            return self._latest_heartbeat

    def is_data_updated(self) -> bool:
        with self._lock:
            if self._update_counter != self._last_update_counter_checked:
                self._last_update_counter_checked = self._update_counter
                return True
            return False

    def get_data_info(self) -> Dict[str, object]:
        with self._lock:
            latest = self._weather_records[-1] if self._weather_records else None
            return {
                "source_type": "i1",
                "records": len(self._weather_records),
                "latest_timestamp": latest.timestamp_str if latest else None,
                "line_temp_threshold": self._line_temp_alert_threshold,
                "line_temp_timeout": self._line_temp_alert_timeout,
            }

    # ----------------------------
    # 内部辅助
    # ----------------------------
    def _format_timestamp(self, ts: int) -> str:
        dt = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(BJ_TZ)
        return dt.strftime("%Y-%m-%d %H:%M")

    def _get_wire_flag(self, component_id: str, ts: int) -> int:
        alert = self._line_temp_alerts.get(component_id)
        if alert is None:
            return 0
        alert_ts, is_alert = alert
        if not is_alert:
            return 0
        if ts - alert_ts > self._line_temp_alert_timeout:
            return 0
        return 1

    def _record_to_dict(self, record: StoredRecord) -> Dict[str, object]:
        return {
            "timestamp_Beijing": record.timestamp_str,
            "sway_speed_dps": record.sway_speed_dps,
            "temperature_C": record.temperature_c,
            "humidity_RH": record.humidity_rh,
            "pressure_hPa": record.pressure_hpa,
            "lux": record.lux,
            "wire_foreign_object": record.wire_foreign_object,
            "component_id": record.component_id,
            "frame_no": record.frame_no,
            "wind_speed_avg_10min": record.wind_speed_avg_10min,
            "wind_direction_deg": record.wind_direction_deg,
            "wind_speed_max": record.wind_speed_max,
            "wind_speed_extreme": record.wind_speed_extreme,
            "precipitation_mm": record.precipitation_mm,
            "precipitation_intensity_mm_min": record.precipitation_intensity_mm_min,
        }


_store_instance: Optional[I1DataStore] = None
_store_lock = threading.Lock()


def initialize_i1_data_store(
    *,
    max_records: int = 288,
    line_temp_alert_threshold: float = 80.0,
    line_temp_alert_timeout: int = 600,
) -> I1DataStore:
    global _store_instance
    with _store_lock:
        if _store_instance is None:
            _store_instance = I1DataStore(
                max_records=max_records,
                line_temp_alert_threshold=line_temp_alert_threshold,
                line_temp_alert_timeout=line_temp_alert_timeout,
            )
        else:
            _store_instance.configure(
                max_records=max_records,
                line_temp_alert_threshold=line_temp_alert_threshold,
                line_temp_alert_timeout=line_temp_alert_timeout,
            )
        return _store_instance


def get_i1_data_store() -> I1DataStore:
    global _store_instance
    with _store_lock:
        if _store_instance is None:
            _store_instance = I1DataStore()
        return _store_instance
