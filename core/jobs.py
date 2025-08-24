import logging
import threading
from typing import Optional


class PeriodicJob:
    """简单的周期性任务封装（基于线程 + Event）"""
    def __init__(self, interval_seconds: int, target, name: str = "PeriodicJob"):
        self.interval_seconds = int(interval_seconds)
        self._target = target
        self._name = name
        self._stop_evt = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name=self._name, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        logger = logging.getLogger(__name__)
        logger.info("[%s] started; interval=%ss", self._name, self.interval_seconds)
        # 先立即执行一次，再进入周期睡眠（如果希望启动后等一个间隔再跑，可以把下面两行对调）
        self._execute_once(logger)
        while not self._stop_evt.wait(self.interval_seconds):
            self._execute_once(logger)
        logger.info("[%s] stopped", self._name)

    def _execute_once(self, logger: logging.Logger) -> None:
        try:
            self._target()
        except Exception as e:
            logger.exception("[%s] execution error: %s", self._name, e)

    def stop(self) -> None:
        self._stop_evt.set()