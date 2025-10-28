from __future__ import annotations

import struct
import time
from dataclasses import dataclass
from typing import Dict, List

from utils.i1.protocol import (
    SYNC_BYTES,
    END_BYTE,
    FRAME_TYPE_UPLINK,
    PACKET_TYPE_WEATHER,
    PACKET_TYPE_TOWER_TILT,
    PACKET_TYPE_LINE_TEMPERATURE,
    PACKET_TYPE_HEARTBEAT,
    PACKET_TYPE_WEATHER_ACK,
    PACKET_TYPE_TOWER_TILT_ACK,
    PACKET_TYPE_LINE_TEMPERATURE_ACK,
    PACKET_TYPE_HEARTBEAT_ACK,
    crc16_modbus,
)


__all__ = [
    "FrameConfig",
    "I1FrameBuilder",
    "generate_default_bundle",
    "PACKET_TYPE_WEATHER",
    "PACKET_TYPE_TOWER_TILT",
    "PACKET_TYPE_LINE_TEMPERATURE",
    "PACKET_TYPE_HEARTBEAT",
    "PACKET_TYPE_WEATHER_ACK",
    "PACKET_TYPE_TOWER_TILT_ACK",
    "PACKET_TYPE_LINE_TEMPERATURE_ACK",
    "PACKET_TYPE_HEARTBEAT_ACK",
]


@dataclass
class WeatherSample:
    component_id: str
    time_stamp: int
    average_wind_speed: float
    average_wind_direction: float
    max_wind_speed: float
    extreme_wind_speed: float
    standard_wind_speed: float
    air_temperature: float
    humidity: float
    air_pressure: float
    precipitation: float
    precipitation_intensity: float
    radiation_intensity: float


@dataclass
class TowerTiltSample:
    component_id: str
    time_stamp: int
    inclination: float
    inclination_x: float
    inclination_y: float
    angle_x: float
    angle_y: float


@dataclass
class LineTemperatureSample:
    component_id: str
    unit_sum: int
    unit_no: int
    time_stamp: int
    line_temperature: float


@dataclass
class HeartbeatSample:
    cmd_id: str
    clocktime_stamp: int
    battery_voltage: float
    operation_temperature: float
    battery_capacity: float
    floating_charge: int
    total_working_time: int
    working_time: int
    connection_state: int
    send_flow: int
    receive_flow: int
    protocol_version: List[int]


@dataclass
class I1SampleBundle:
    weather: List[WeatherSample]
    tower_tilt: List[TowerTiltSample]
    line_temperature: List[LineTemperatureSample]
    heartbeat: List[HeartbeatSample]


@dataclass
class FrameConfig:
    frame_type_uplink: int
    packet_types: Dict[str, int]


class I1FrameBuilder:
    def __init__(self, cfg: FrameConfig) -> None:
        self.cfg = cfg

    def build_weather(self, sample: WeatherSample, frame_no: int, cmd_id: str) -> bytes:
        packet_type = self.cfg.packet_types["weather"]
        content = bytearray()
        content.extend(_encode_component_id(sample.component_id))
        content.extend(struct.pack("<I", sample.time_stamp))
        content.extend(struct.pack("<f", sample.average_wind_speed))
        content.extend(struct.pack("<H", int(round(sample.average_wind_direction)) % 360))
        content.extend(struct.pack("<f", sample.max_wind_speed))
        content.extend(struct.pack("<f", sample.extreme_wind_speed))
        content.extend(struct.pack("<f", sample.standard_wind_speed))
        content.extend(struct.pack("<f", sample.air_temperature))
        content.extend(struct.pack("<H", _clamp_u16(int(round(sample.humidity * 10)))))
        content.extend(struct.pack("<f", sample.air_pressure))
        content.extend(struct.pack("<f", sample.precipitation))
        content.extend(struct.pack("<f", sample.precipitation_intensity))
        content.extend(struct.pack("<H", _clamp_u16(int(round(sample.radiation_intensity)))))
        return _build_frame(cmd_id, packet_type, frame_no, content)

    def build_tower_tilt(self, sample: TowerTiltSample, frame_no: int, cmd_id: str) -> bytes:
        packet_type = self.cfg.packet_types["tower_tilt"]
        content = bytearray()
        content.extend(_encode_component_id(sample.component_id))
        content.extend(struct.pack("<I", sample.time_stamp))
        content.extend(struct.pack("<f", sample.inclination))
        content.extend(struct.pack("<f", sample.inclination_x))
        content.extend(struct.pack("<f", sample.inclination_y))
        content.extend(struct.pack("<f", sample.angle_x))
        content.extend(struct.pack("<f", sample.angle_y))
        return _build_frame(cmd_id, packet_type, frame_no, content)

    def build_line_temperature(self, sample: LineTemperatureSample, frame_no: int, cmd_id: str) -> bytes:
        packet_type = self.cfg.packet_types["line_temperature"]
        content = bytearray()
        content.extend(_encode_component_id(sample.component_id))
        content.append(sample.unit_sum & 0xFF)
        content.append(sample.unit_no & 0xFF)
        content.extend(struct.pack("<I", sample.time_stamp))
        content.extend(struct.pack("<f", sample.line_temperature))
        return _build_frame(cmd_id, packet_type, frame_no, content)

    def build_heartbeat(self, sample: HeartbeatSample, frame_no: int) -> bytes:
        packet_type = self.cfg.packet_types["heartbeat"]
        content = bytearray()
        content.extend(struct.pack("<I", sample.clocktime_stamp))
        content.extend(struct.pack("<f", sample.battery_voltage))
        content.extend(struct.pack("<f", sample.operation_temperature))
        content.extend(struct.pack("<f", sample.battery_capacity))
        content.append(sample.floating_charge & 0xFF)
        content.extend(struct.pack("<I", sample.total_working_time))
        content.extend(struct.pack("<I", sample.working_time))
        content.append(sample.connection_state & 0xFF)
        content.extend(struct.pack("<I", sample.send_flow))
        content.extend(struct.pack("<I", sample.receive_flow))
        version = bytes((v & 0xFF) for v in sample.protocol_version[:4])
        if len(version) < 4:
            version = version.ljust(4, b"\x00")
        content.extend(version)
        return _build_frame(sample.cmd_id, packet_type, frame_no, content)


def generate_default_bundle() -> I1SampleBundle:
    now = int(time.time())
    weather_sample = WeatherSample(
        component_id="WS-001",
        time_stamp=now - 120,
        average_wind_speed=5.2,
        average_wind_direction=135.0,
        max_wind_speed=8.1,
        extreme_wind_speed=12.3,
        standard_wind_speed=1.2,
        air_temperature=26.5,
        humidity=68.0,
        air_pressure=1009.8,
        precipitation=0.6,
        precipitation_intensity=0.02,
        radiation_intensity=820.0,
    )

    tower_sample = TowerTiltSample(
        component_id="TT-301",
        time_stamp=now - 300,
        inclination=2.6,
        inclination_x=1.2,
        inclination_y=2.3,
        angle_x=0.35,
        angle_y=0.27,
    )

    line_samples = [
        LineTemperatureSample(
            component_id="LT-501",
            unit_sum=3,
            unit_no=1,
            time_stamp=now - 60,
            line_temperature=52.4,
        ),
        LineTemperatureSample(
            component_id="LT-501",
            unit_sum=3,
            unit_no=2,
            time_stamp=now - 60,
            line_temperature=51.9,
        ),
        LineTemperatureSample(
            component_id="LT-501",
            unit_sum=3,
            unit_no=3,
            time_stamp=now - 60,
            line_temperature=52.8,
        ),
    ]

    heartbeat_sample = HeartbeatSample(
        cmd_id="HB-CTRL-01",
        clocktime_stamp=now,
        battery_voltage=3.95,
        operation_temperature=34.5,
        battery_capacity=85.0,
        floating_charge=0x01,
        total_working_time=24 * 3600,
        working_time=6 * 3600,
        connection_state=0x00,
        send_flow=123456,
        receive_flow=234567,
        protocol_version=[0x01, 0x02, 0x04, 0x0A],
    )

    return I1SampleBundle(
        weather=[weather_sample],
        tower_tilt=[tower_sample],
        line_temperature=line_samples,
        heartbeat=[heartbeat_sample],
    )


def _encode_component_id(component_id: str) -> bytes:
    data = component_id.encode("ascii", errors="ignore")[:17]
    return data.ljust(17, b"\x00")


def _build_frame(cmd_id: str, packet_type: int, frame_no: int, content: bytes) -> bytes:
    header = bytearray()
    header.extend(SYNC_BYTES)
    header.extend(struct.pack("<H", len(content)))
    header.extend(_encode_component_id(cmd_id))
    header.append(FRAME_TYPE_UPLINK)
    header.append(packet_type & 0xFF)
    header.append(frame_no & 0xFF)
    header.extend(content)
    crc = crc16_modbus(header[2:])
    header.extend(struct.pack("<H", crc))
    header.append(END_BYTE)
    return bytes(header)


def _clamp_u16(value: int) -> int:
    return max(0, min(0xFFFF, value))