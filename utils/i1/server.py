"""I1 TCP 服务端，实现协议接入。"""
from __future__ import annotations

import logging
import socket
import struct
import threading
import socketserver
from typing import Optional, Tuple

from .protocol import (
    SYNC_BYTES,
    FRAME_TYPE_UPLINK,
    WeatherPayload,
    TowerTiltPayload,
    LineTemperaturePayload,
    HeartbeatPayload,
    I1ProtocolError,
    parse_uplink_frame,
    build_ack_frame,
)
from .store import get_i1_data_store

logger = logging.getLogger(__name__)


class I1TCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

    def __init__(self, server_address, RequestHandlerClass, store, bind_and_activate: bool = True):
        super().__init__(server_address, RequestHandlerClass, bind_and_activate=bind_and_activate)
        self.store = store


class I1RequestHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        client = f"{self.client_address[0]}:{self.client_address[1]}"
        logger.info("I1 连接建立: %s", client)
        buffer = bytearray()

        try:
            self.request.settimeout(30.0)
        except Exception:  # pragma: no cover - 一些平台 socket 不支持 settimeout
            pass

        try:
            while True:
                try:
                    chunk = self.request.recv(4096)
                except socket.timeout:
                    continue
                if not chunk:
                    break
                buffer.extend(chunk)

                while True:
                    frame, remaining = _extract_frame(buffer)
                    if frame is None:
                        buffer = remaining
                        break
                    buffer = remaining
                    self._handle_frame(frame)
        except Exception as exc:
            logger.exception("I1 连接处理异常: %s", exc)
        finally:
            logger.info("I1 连接关闭: %s", client)

    # ----------------------------
    # 内部处理
    # ----------------------------
    def _handle_frame(self, frame: bytes) -> None:
        header_info = _safe_peek_header(frame)
        try:
            parsed = parse_uplink_frame(frame)
            self._dispatch_payload(parsed)
            ack = build_ack_frame(parsed.cmd_id, parsed.packet_type, parsed.frame_no, success=True)
        except I1ProtocolError as exc:
            logger.warning("I1 帧解析失败: %s", exc)
            if header_info is not None:
                cmd_id, packet_type, frame_no = header_info
                ack = build_ack_frame(cmd_id, packet_type, frame_no, success=False)
            else:
                return  # 无法取到头信息，直接丢弃
        except Exception as exc:  # pragma: no cover - 防御性
            logger.exception("I1 帧处理异常: %s", exc)
            if header_info is not None:
                cmd_id, packet_type, frame_no = header_info
                ack = build_ack_frame(cmd_id, packet_type, frame_no, success=False)
            else:
                return

        try:
            self.request.sendall(ack)
        except Exception as exc:
            logger.warning("I1 ACK 发送失败: %s", exc)

    def _dispatch_payload(self, parsed) -> None:
        store = self.server.store  # type: ignore[attr-defined]
        payload = parsed.payload
        if isinstance(payload, WeatherPayload):
            store.add_weather(payload, parsed.frame_no)
        elif isinstance(payload, TowerTiltPayload):
            store.add_tower_tilt(payload)
        elif isinstance(payload, LineTemperaturePayload):
            store.add_line_temperature(payload)
        elif isinstance(payload, HeartbeatPayload):
            store.add_heartbeat(payload)
        else:  # pragma: no cover - 理论不可达
            logger.debug("收到未处理的 payload 类型: %s", type(payload))


def _extract_frame(buffer: bytearray) -> Tuple[Optional[bytes], bytearray]:
    if not buffer:
        return None, buffer

    max_scan = len(buffer) - 1
    start_index = -1
    for idx in range(max_scan):
        if buffer[idx:idx + 2] == SYNC_BYTES:
            start_index = idx
            break
    if start_index == -1:
        # 未找到同步头，保留末尾一个字节以防 0x5A
        return None, buffer[-1:]

    if start_index > 0:
        buffer = buffer[start_index:]

    if len(buffer) < 2 + 2:
        return None, buffer

    packet_length = struct.unpack_from("<H", buffer, 2)[0]
    expected_len = 2 + 2 + 17 + 1 + 1 + 1 + packet_length + 2 + 1
    if packet_length <= 0 or expected_len > 4096:
        # 异常长度，跳过本次同步头
        return None, buffer[2:]

    if len(buffer) < expected_len:
        return None, buffer

    frame = bytes(buffer[:expected_len])
    remaining = buffer[expected_len:]
    return frame, remaining


def _safe_peek_header(frame: bytes) -> Optional[Tuple[str, int, int]]:
    base_len = 2 + 2 + 17 + 1 + 1 + 1
    if len(frame) < base_len:
        return None
    cmd_id_raw = frame[4:21]
    packet_type = frame[22]
    frame_no = frame[23]
    try:
        cmd_id = cmd_id_raw.rstrip(b"\x00").decode("ascii", errors="ignore")
    except Exception:
        cmd_id = ""
    return cmd_id, packet_type, frame_no


class _ServerManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._server: Optional[I1TCPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self, host: str, port: int, store=None) -> None:
        with self._lock:
            if self._server is not None:
                return
            if store is None:
                store = get_i1_data_store()
            server = I1TCPServer((host, port), I1RequestHandler, store)
            thread = threading.Thread(target=server.serve_forever, name="I1TCPServer", daemon=True)
            thread.start()
            logger.info("I1 TCP 服务已启动，监听 %s:%s", host, port)
            self._server = server
            self._thread = thread

    def stop(self) -> None:
        with self._lock:
            if self._server is None:
                return
            self._server.shutdown()
            self._server.server_close()
            logger.info("I1 TCP 服务已停止")
            self._server = None
            self._thread = None


_server_manager = _ServerManager()


def start_i1_tcp_server(host: str, port: int, store=None) -> None:
    _server_manager.start(host, port, store)


def stop_i1_tcp_server() -> None:
    _server_manager.stop()
