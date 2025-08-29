# utils/GetImage.py
from __future__ import annotations
import time
from pathlib import Path
from threading import Lock
from typing import Optional

import cv2
import numpy as np

# 路径约定：本文件同级的 data/ 目录
_DATA_DIR = Path(__file__).resolve().parent / "data"
_IMG_NAME = "test_image.jpg"
_NUM_FILE = "TestImageNumber.txt"

# 进程内简单互斥，避免并发竞态（仅对同一进程内多线程有效）
_LOCK = Lock()


def _ensure_data_dir() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def _read_number(p: Path) -> int:
    """读取计数值，缺省或解析失败时视为 0；范围归一到 [0,99]。"""
    try:
        s = p.read_text(encoding="utf-8").strip()
        n = int(s)
    except FileNotFoundError:
        n = 0
    except Exception:
        n = 0
    return n % 100


def _write_number(p: Path, n: int) -> None:
    p.write_text(str(n % 100), encoding="utf-8")


def _draw_number_top_left(img: np.ndarray, text: str) -> np.ndarray:
    """
    在图像左上角绘制文字（带背景块，便于可读）。
    返回绘制后的新图（不修改原图引用）。
    """
    out = img.copy()
    font = cv2.FONT_HERSHEY_SIMPLEX

    # 自适应字号/粗细（按较大边）
    base = max(out.shape[0], out.shape[1])
    scale = max(0.6, min(3.0, base / 600.0 * 1.1))
    thickness = max(1, int(scale * 2))

    (tw, th), baseline = cv2.getTextSize(text, font, scale, thickness)
    pad = int(8 * scale)
    x, y = pad + 2, pad + th  # 左上角内边距

    # 背景矩形（半透明效果：先画实心再融合）
    bg = out.copy()
    cv2.rectangle(
        bg,
        (pad, pad),
        (pad + tw + pad, pad + th + baseline + pad),
        color=(0, 0, 0),
        thickness=-1,
    )
    alpha = 0.35  # 透明度
    cv2.addWeighted(bg, alpha, out, 1 - alpha, 0, out)

    # 白字 + 细黑描边提升对比
    cv2.putText(out, text, (x, y), font, scale, (0, 0, 0), thickness + 2, cv2.LINE_AA)
    cv2.putText(out, text, (x, y), font, scale, (255, 255, 255), thickness, cv2.LINE_AA)
    return out


def get_processed_image(return_rgb: bool = False) -> np.ndarray:
    """
    读取 data/test_image.jpg、在左上角绘制 TestImageNumber.txt 的数字，
    然后把数字加 1 取模 100 写回，delay 200ms，最后返回**绘制后的图像**。

    参数：
        return_rgb: 若为 True，则返回 RGB；否则返回 OpenCV 习惯的 BGR。

    返回：
        numpy.ndarray 图像数组（BGR 或 RGB）
    """
    _ensure_data_dir()
    img_path = _DATA_DIR / _IMG_NAME
    num_path = _DATA_DIR / _NUM_FILE

    with _LOCK:
        img = cv2.imread(str(img_path), cv2.IMREAD_COLOR)
        if img is None:
            raise FileNotFoundError(f"无法读取图片：{img_path}")

        n = _read_number(num_path)
        drawn = _draw_number_top_left(img, str(n))

        # 增加计数并写回
        _write_number(num_path, (n + 1) % 100)

        # 使用配置的异物检测间隔
        try:
            from config.settings import AppConfig
            delay = AppConfig().foreign_object_check_interval_sec
        except ImportError:
            delay = 0.2  # 默认延迟
        
        time.sleep(delay)

    if return_rgb:
        return cv2.cvtColor(drawn, cv2.COLOR_BGR2RGB)
    return drawn


def get_processed_image_bytes(jpeg_quality: int = 90) -> bytes:
    """
    获取处理后的 JPEG 二进制（便于 Flask 直接响应）。
    """
    img = get_processed_image(return_rgb=False)  # OpenCV 按 BGR 编码
    ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), int(jpeg_quality)])
    if not ok:
        raise RuntimeError("JPEG 编码失败")
    return buf.tobytes()


if __name__ == "__main__":
    # 自测：将处理结果写到 data/last_test_output.jpg
    _ensure_data_dir()
    out_file = _DATA_DIR / "last_test_output.jpg"
    arr = get_processed_image()
    ok = cv2.imwrite(str(out_file), arr)
    print(f"输出文件：{out_file}（写入成功：{ok}）")
