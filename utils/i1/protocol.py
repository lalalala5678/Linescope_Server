"""I1 协议解析与响应构建。"""
from __future__ import annotations

import struct
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, Union

SYNC_BYTES = b"\x5A\xA5"
END_BYTE = 0x96

# I1 协议定义的帧类型:
FRAME_TYPE_UPLINK = 0x01
FRAME_TYPE_DOWNLINK = 0x02

# Packet Type 定义（依据接口文档及示例约定）
PACKET_TYPE_WEATHER = 0x31
PACKET_TYPE_TOWER_TILT = 0x32
PACKET_TYPE_LINE_TEMPERATURE = 0x33
PACKET_TYPE_HEARTBEAT = 0x61

PACKET_TYPE_WEATHER_ACK = 0xB1
PACKET_TYPE_TOWER_TILT_ACK = 0xB2
PACKET_TYPE_LINE_TEMPERATURE_ACK = 0xB3
PACKET_TYPE_HEARTBEAT_ACK = 0xE1

ACK_TYPE_MAP: Dict[int, int] = {
    PACKET_TYPE_WEATHER: PACKET_TYPE_WEATHER_ACK,
    PACKET_TYPE_TOWER_TILT: PACKET_TYPE_TOWER_TILT_ACK,
    PACKET_TYPE_LINE_TEMPERATURE: PACKET_TYPE_LINE_TEMPERATURE_ACK,
    PACKET_TYPE_HEARTBEAT: PACKET_TYPE_HEARTBEAT_ACK,
}


class I1ProtocolError(Exception):
    """协议解析错误基类。"""


class FrameSyncError(I1ProtocolError):
    """同步头错误。"""


class CRCMismatchError(I1ProtocolError):
    """CRC 校验失败。"""


class UnsupportedPacketTypeError(I1ProtocolError):
    """收到未支持的 Packet Type。"""


@dataclass(frozen=True)
class WeatherPayload:
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


@dataclass(frozen=True)
class TowerTiltPayload:
    component_id: str
    time_stamp: int
    inclination: float
    inclination_x: float
    inclination_y: float
    angle_x: float
    angle_y: float


@dataclass(frozen=True)
class LineTemperaturePayload:
    component_id: str
    unit_sum: int
    unit_no: int
    time_stamp: int
    line_temperature: float


@dataclass(frozen=True)
class HeartbeatPayload:
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
    protocol_version: Tuple[int, int, int, int]


ParsedPayload = Union[WeatherPayload, TowerTiltPayload, LineTemperaturePayload, HeartbeatPayload]


@dataclass(frozen=True)
class ParsedFrame:
    raw_frame: bytes
    packet_length: int
    cmd_id: str
    frame_type: int
    packet_type: int
    frame_no: int
    payload: ParsedPayload


def crc16_modbus(data: bytes) -> int:
    """计算 Modbus CRC16 (poly 0xA001)。"""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF


def _decode_ascii(raw: bytes) -> str:
    return raw.rstrip(b"\x00").decode("ascii", errors="ignore")


def _read_float(data: bytes, offset: int) -> Tuple[float, int]:
    value = struct.unpack_from("<f", data, offset)[0]
    return value, offset + 4


def _read_uint16(data: bytes, offset: int) -> Tuple[int, int]:
    value = struct.unpack_from("<H", data, offset)[0]
    return value, offset + 2


def _read_uint32(data: bytes, offset: int) -> Tuple[int, int]:
    value = struct.unpack_from("<I", data, offset)[0]
    return value, offset + 4


def parse_uplink_frame(frame: bytes) -> ParsedFrame:
    """解析上传帧，返回结构化结果。"""
    if len(frame) < 2 + 2 + 17 + 1 + 1 + 1 + 2 + 1:
        raise I1ProtocolError("帧长度不足")

    if frame[:2] != SYNC_BYTES:
        raise FrameSyncError("Sync 头校验失败")

    packet_length = struct.unpack_from("<H", frame, 2)[0]
    expected_len = 2 + 2 + 17 + 1 + 1 + 1 + packet_length + 2 + 1
    if len(frame) != expected_len:
        raise I1ProtocolError(f"帧长度与 Packet_Length 不一致: {len(frame)} != {expected_len}")

    if frame[-1] != END_BYTE:
        raise I1ProtocolError("帧尾校验失败")

    crc_expected = struct.unpack_from("<H", frame, len(frame) - 3)[0]
    crc_actual = crc16_modbus(frame[2:-3])
    if crc_expected != crc_actual:
        raise CRCMismatchError(f"CRC 校验失败: expect=0x{crc_expected:04X}, actual=0x{crc_actual:04X}")

    cmd_id_raw = frame[4:21]
    frame_type = frame[21]
    packet_type = frame[22]
    frame_no = frame[23]
    content = frame[24:24 + packet_length]

    cmd_id = _decode_ascii(cmd_id_raw)

    payload: ParsedPayload
    if packet_type == PACKET_TYPE_WEATHER:
        payload = _parse_weather_payload(content)
    elif packet_type == PACKET_TYPE_TOWER_TILT:
        payload = _parse_tower_tilt_payload(content)
    elif packet_type == PACKET_TYPE_LINE_TEMPERATURE:
        payload = _parse_line_temperature_payload(content)
    elif packet_type == PACKET_TYPE_HEARTBEAT:
        payload = _parse_heartbeat_payload(content, cmd_id)
    else:
        raise UnsupportedPacketTypeError(f"暂不支持的 Packet_Type: 0x{packet_type:02X}")

    return ParsedFrame(
        raw_frame=frame,
        packet_length=packet_length,
        cmd_id=cmd_id,
        frame_type=frame_type,
        packet_type=packet_type,
        frame_no=frame_no,
        payload=payload,
    )


def _parse_weather_payload(content: bytes) -> WeatherPayload:
    if len(content) < 17 + 4 + 4 + 2 + 4 + 4 + 4 + 4 + 2 + 4 + 4 + 4 + 2:
        raise I1ProtocolError("天气数据内容长度不足")

    offset = 0
    component_id = _decode_ascii(content[offset:offset + 17])
    offset += 17

    time_stamp, offset = _read_uint32(content, offset)
    avg_ws, offset = _read_float(content, offset)
    avg_wd_raw, offset = _read_uint16(content, offset)
    max_ws, offset = _read_float(content, offset)
    extreme_ws, offset = _read_float(content, offset)
    standard_ws, offset = _read_float(content, offset)
    air_temp, offset = _read_float(content, offset)
    humidity_raw, offset = _read_uint16(content, offset)
    air_pressure, offset = _read_float(content, offset)
    precipitation, offset = _read_float(content, offset)
    precipitation_intensity, offset = _read_float(content, offset)
    radiation_raw, offset = _read_uint16(content, offset)

    humidity = humidity_raw / 10.0
    average_wind_direction = float(avg_wd_raw)
    radiation_intensity = float(radiation_raw)

    return WeatherPayload(
        component_id=component_id,
        time_stamp=time_stamp,
        average_wind_speed=avg_ws,
        average_wind_direction=average_wind_direction,
        max_wind_speed=max_ws,
        extreme_wind_speed=extreme_ws,
        standard_wind_speed=standard_ws,
        air_temperature=air_temp,
        humidity=humidity,
        air_pressure=air_pressure,
        precipitation=precipitation,
        precipitation_intensity=precipitation_intensity,
        radiation_intensity=radiation_intensity,
    )


def _parse_tower_tilt_payload(content: bytes) -> TowerTiltPayload:
    if len(content) < 17 + 4 + 4 + 4 + 4 + 4 + 4:
        raise I1ProtocolError("倾角数据内容长度不足")

    offset = 0
    component_id = _decode_ascii(content[offset:offset + 17])
    offset += 17

    time_stamp, offset = _read_uint32(content, offset)
    inclination, offset = _read_float(content, offset)
    inclination_x, offset = _read_float(content, offset)
    inclination_y, offset = _read_float(content, offset)
    angle_x, offset = _read_float(content, offset)
    angle_y, offset = _read_float(content, offset)

    return TowerTiltPayload(
        component_id=component_id,
        time_stamp=time_stamp,
        inclination=inclination,
        inclination_x=inclination_x,
        inclination_y=inclination_y,
        angle_x=angle_x,
        angle_y=angle_y,
    )


def _parse_line_temperature_payload(content: bytes) -> LineTemperaturePayload:
    if len(content) < 17 + 1 + 1 + 4 + 4:
        raise I1ProtocolError("导线温度内容长度不足")

    offset = 0
    component_id = _decode_ascii(content[offset:offset + 17])
    offset += 17

    unit_sum = content[offset]
    offset += 1
    unit_no = content[offset]
    offset += 1
    time_stamp, offset = _read_uint32(content, offset)
    line_temperature, offset = _read_float(content, offset)

    return LineTemperaturePayload(
        component_id=component_id,
        unit_sum=unit_sum,
        unit_no=unit_no,
        time_stamp=time_stamp,
        line_temperature=line_temperature,
    )


def _parse_heartbeat_payload(content: bytes, cmd_id: str) -> HeartbeatPayload:
    if len(content) < 4 + 4 + 4 + 1 + 4 + 4 + 1 + 4 + 4 + 4:
        raise I1ProtocolError("心跳内容长度不足")

    offset = 0
    clocktime_stamp, offset = _read_uint32(content, offset)
    battery_voltage, offset = _read_float(content, offset)
    operation_temperature, offset = _read_float(content, offset)
    battery_capacity, offset = _read_float(content, offset)
    floating_charge = content[offset]
    offset += 1
    total_working_time, offset = _read_uint32(content, offset)
    working_time, offset = _read_uint32(content, offset)
    connection_state = content[offset]
    offset += 1
    send_flow, offset = _read_uint32(content, offset)
    receive_flow, offset = _read_uint32(content, offset)
    protocol_version_raw = content[offset:offset + 4]

    if len(protocol_version_raw) != 4:
        raise I1ProtocolError("协议版本字段长度不足")

    protocol_version = tuple(protocol_version_raw)

    return HeartbeatPayload(
        cmd_id=cmd_id,
        clocktime_stamp=clocktime_stamp,
        battery_voltage=battery_voltage,
        operation_temperature=operation_temperature,
        battery_capacity=battery_capacity,
        floating_charge=floating_charge,
        total_working_time=total_working_time,
        working_time=working_time,
        connection_state=connection_state,
        send_flow=send_flow,
        receive_flow=receive_flow,
        protocol_version=protocol_version,  # type: ignore[arg-type]
    )


def build_ack_frame(
    cmd_id: str,
    packet_type: int,
    frame_no: int,
    *,
    success: bool = True,
    mode: int = 0x00,
    clocktime_stamp: Optional[int] = None,
) -> bytes:
    """根据上行帧构建 ACK。"""
    ack_packet_type = ACK_TYPE_MAP.get(packet_type, packet_type)
    cmd_id_bytes = cmd_id.encode("ascii", errors="ignore")[:17]
    cmd_id_bytes = cmd_id_bytes.ljust(17, b"\x00")

    if packet_type == PACKET_TYPE_HEARTBEAT:
        if clocktime_stamp is None:
            clocktime_stamp = int(time.time())
        content = bytes([
            0xFF if success else 0x00,
            mode & 0xFF,
        ]) + struct.pack("<I", clocktime_stamp)
    else:
        content = bytes([0xFF if success else 0x00])

    packet_length = len(content)
    header = bytearray()
    header.extend(SYNC_BYTES)
    header.extend(struct.pack("<H", packet_length))
    header.extend(cmd_id_bytes)
    header.append(FRAME_TYPE_DOWNLINK)
    header.append(ack_packet_type & 0xFF)
    header.append(frame_no & 0xFF)
    header.extend(content)

    crc = crc16_modbus(header[2:])
    header.extend(struct.pack("<H", crc))
    header.append(END_BYTE)
    return bytes(header)
