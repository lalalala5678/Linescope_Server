import time
import logging
from typing import Generator

import cv2
import numpy as np
from utils.GetImage import get_processed_image


def mjpeg_generator(frame_interval: float = 0) -> Generator[bytes, None, None]:
    """
    MJPEG 生成器：持续获取一帧图片 -> JPEG 编码 -> multipart chunk。
    - frame_interval: 帧间隔（秒），避免 CPU 占用过高
    """
    logger = logging.getLogger(__name__)
    boundary = b"--frame"
    while True:
        try:
            # 1) 获取一帧图像（BGR, uint8, HxWx3）
            frame: np.ndarray = get_processed_image()
            if not isinstance(frame, np.ndarray) or frame.ndim != 3 or frame.shape[2] != 3:
                logger.warning("get_processed_image returned unexpected array shape: %s", getattr(frame, "shape", None))
                time.sleep(frame_interval)
                continue

            # 2) OpenCV JPEG 编码
            ok, buf = cv2.imencode(".jpg", frame)
            if not ok:
                logger.warning("cv2.imencode('.jpg', frame) failed")
                time.sleep(frame_interval)
                continue

            jpg: bytes = buf.tobytes()

            # 3) multipart/x-mixed-replace chunk
            yield (
                boundary
                + b"\r\n"
                + b"Content-Type: image/jpeg\r\n"
                + f"Content-Length: {len(jpg)}\r\n\r\n".encode("utf-8")
                + jpg
                + b"\r\n"
            )

            # 控制输出频率
            time.sleep(frame_interval)

        except GeneratorExit:
            # 客户端断开，生成器被关闭
            logger.info("Client disconnected from MJPEG stream.")
            break
        except Exception as e:
            logger.exception("Error in MJPEG generator: %s", e)
            time.sleep(max(0.5, frame_interval))