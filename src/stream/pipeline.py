import logging
import threading
from typing import Any

from stream.receive import receive

logger = logging.getLogger(__name__)


class Pipeline:
    def __init__(
        self,
        arguments: Any,
    ) -> None:
        self._arguments = arguments
        self._stop_event = threading.Event()
        self._started = False
        self._thread = threading.Thread(
            target=self._run,
            name="video-pipeline",
        )

    @property
    def isRunning(self) -> bool:
        return self._thread.is_alive()

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._thread.start()

    def stop(self) -> None:
        logger.info("Video pipeline stop requested.")
        self._stop_event.set()
        if self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def _run(self) -> None:
        logger.info("Video pipeline thread started: %s", self._arguments.process_id)
        self.run()

    def run(self) -> None:
        try:
            for packet in receive(self._arguments, self._stop_event):
                if self._stop_event.is_set():
                    break
                logger.debug("Video pipeline received packet: %s", packet)
        finally:
            logger.info("Video pipeline thread stopped: %s", self._arguments.process_id)
