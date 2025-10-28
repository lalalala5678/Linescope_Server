#!/usr/bin/env python3
"""
简单的示例脚本：生成一份 I1 数据集并通过 TCP 推送到 Linescope Server。

"""
from __future__ import annotations

import argparse
import json
import socket
import struct
import sys
import time
from pathlib import Path
from typing import List, Tuple


REPO_ROOT = Path(__file__).resolve().parent
SERVER_ROOT = REPO_ROOT / "Linescope_Server"

if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from interfaces.i1 import (  # type: ignore  # noqa: E402
    FrameConfig,
    I1FrameBuilder,
    generate_default_bundle,
    PACKET_TYPE_WEATHER,
    PACKET_TYPE_TOWER_TILT,
    PACKET_TYPE_LINE_TEMPERATURE,
    PACKET_TYPE_HEARTBEAT,
    PACKET_TYPE_WEATHER_ACK,
    PACKET_TYPE_TOWER_TILT_ACK,
    PACKET_TYPE_LINE_TEMPERATURE_ACK,
    PACKET_TYPE_HEARTBEAT_ACK,
)
from interfaces.i1.encoding import crc16_modbus  # type: ignore  # noqa: E402


SYNC_BYTES = b"\x5A\xA5"
END_BYTE = b"\x96"


def build_sample_frames() -> List[Tuple[str, bytes]]:
    bundle = generate_default_bundle()
    frame_cfg = FrameConfig(
        frame_type_uplink=1,
        packet_types={
            "weather": PACKET_TYPE_WEATHER,
            "tower_tilt": PACKET_TYPE_TOWER_TILT,
            "line_temperature": PACKET_TYPE_LINE_TEMPERATURE,
            "heartbeat": PACKET_TYPE_HEARTBEAT,
        },
    )
    builder = I1FrameBuilder(frame_cfg)

    frames: List[Tuple[str, bytes]] = []
    frame_counter = 0

    # 最新的气象样本
    if bundle.weather:
        sample = bundle.weather[-1]
        frames.append(
            (
                "weather",
                builder.build_weather(sample, frame_counter, sample.component_id),
            )
        )
        frame_counter = (frame_counter + 1) % 256

    # 最新的杆塔倾斜样本
    if bundle.tower_tilt:
        sample = bundle.tower_tilt[-1]
        frames.append(
            (
                "tower_tilt",
                builder.build_tower_tilt(sample, frame_counter, sample.component_id),
            )
        )
        frame_counter = (frame_counter + 1) % 256

    # 同一时间戳下的所有导线温度单元
    if bundle.line_temperature:
        latest_ts = bundle.line_temperature[-1].time_stamp
        latest_set = [s for s in bundle.line_temperature if s.time_stamp == latest_ts]
        for sample in latest_set:
            frames.append(
                (
                    "line_temperature",
                    builder.build_line_temperature(sample, frame_counter, sample.component_id),
                )
            )
            frame_counter = (frame_counter + 1) % 256

    # 最新心跳
    if bundle.heartbeat:
        sample = bundle.heartbeat[-1]
        frames.append(
            (
                "heartbeat",
                builder.build_heartbeat(sample, frame_counter),
            )
        )
        frame_counter = (frame_counter + 1) % 256

    return frames


def _read_exact(sock: socket.socket, size: int, timeout: float) -> bytes:
    sock.settimeout(timeout)
    data = bytearray()
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise ConnectionError("连接已关闭")
        data.extend(chunk)
    return bytes(data)


def _receive_frame(sock: socket.socket, timeout: float) -> bytes:
    sync = _read_exact(sock, 2, timeout)
    while sync != SYNC_BYTES:
        next_byte = _read_exact(sock, 1, timeout)
        sync = sync[1:] + next_byte
    length_bytes = _read_exact(sock, 2, timeout)
    packet_length = struct.unpack("<H", length_bytes)[0]
    remaining = _read_exact(sock, 17 + 1 + 1 + 1 + packet_length + 2 + 1, timeout)
    frame = SYNC_BYTES + length_bytes + remaining
    if frame[-1:] != END_BYTE:
        raise ValueError("应答帧结尾不正确")
    crc_expected = struct.unpack("<H", frame[-3:-1])[0]
    crc_actual = crc16_modbus(frame[2:-3])
    if crc_expected != crc_actual:
        raise ValueError("应答帧 CRC 校验失败")
    return frame


def _decode_cmd_id(raw: bytes) -> str:
    return raw.rstrip(b"\x00").decode("ascii", errors="ignore") or ""


def parse_ack(frame: bytes) -> dict:
    packet_length = struct.unpack("<H", frame[2:4])[0]
    cmd_id = _decode_cmd_id(frame[4:21])
    frame_type = frame[21]
    packet_type = frame[22]
    frame_no = frame[23]
    content = frame[24:24 + packet_length]

    info = {
        "cmd_id": cmd_id,
        "frame_type": frame_type,
        "packet_type": packet_type,
        "frame_no": frame_no,
    }

    if packet_type in {PACKET_TYPE_WEATHER_ACK, PACKET_TYPE_TOWER_TILT_ACK, PACKET_TYPE_LINE_TEMPERATURE_ACK}:
        info.update({"data_status": content[0] if content else None})
    elif packet_type == PACKET_TYPE_HEARTBEAT_ACK:
        if len(content) >= 6:
            info.update({
                "command_status": content[0],
                "mode": content[1],
                "clocktime_stamp": struct.unpack("<I", content[2:6])[0],
            })
        else:
            info.update({"command_status": None, "mode": None, "clocktime_stamp": None})
    else:
        info.update({"raw_content": content.hex()})
    return info


def send_frames_over_tcp(host: str, port: int, frames: List[Tuple[str, bytes]], timeout: float, repeat: int, interval: float) -> None:
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            print(f"已连接到 TCP 服务器 {host}:{port}")
            for turn in range(1, repeat + 1):
                print(f"\n=== 第 {turn} 轮推送，共 {len(frames)} 帧 ===")
                for frame_kind, frame_bytes in frames:
                    sock.sendall(frame_bytes)
                    ack_frame = _receive_frame(sock, timeout)
                    ack = parse_ack(ack_frame)
                    print(f"发送 {frame_kind} 帧 -> Frame_No={ack['frame_no']} Packet_Type=0x{ack['packet_type']:02X}")
                    print("  ACK:", json.dumps(ack, ensure_ascii=False))
                    time.sleep(0.2)
                if turn < repeat:
                    time.sleep(max(0.0, interval))
    except (OSError, ValueError, ConnectionError) as exc:
        print(f"[ERROR] TCP 交互失败: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="将示例 I1 数据推送到 Linescope Server")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="TCP 服务器地址（默认: 127.0.0.1）",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9100,
        help="TCP 服务器端口（默认: 9100）",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="推送次数（默认: 1）",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="多次推送之间的间隔秒数（默认: 2.0）",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="TCP 读写超时时间（秒，默认: 10.0）",
    )

    args = parser.parse_args()

    frames = build_sample_frames()
    if not frames:
        print("未生成任何示例帧，无法推送")
        return

    send_frames_over_tcp(args.host, args.port, frames, timeout=args.timeout, repeat=max(1, args.repeat), interval=args.interval)


if __name__ == "__main__":
    main()
