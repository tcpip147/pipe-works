"""Asynchronous GPU inference-result copies for the video pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable
import logging
import queue
import threading

import torch


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class _PendingResult:
    cpu_result: torch.Tensor
    ready: torch.cuda.Event
    dependency: torch.cuda.Event


class InferenceResultQueue:
    """Publish completed CPU copies without back-pressuring the frame stream."""

    def __init__(
        self,
        queue_size: int = 30,
        consumer: Callable[[torch.Tensor], None] | None = None,
    ) -> None:
        self.cpu_queue: queue.Queue[torch.Tensor] = queue.Queue(maxsize=queue_size)
        self._consumer = consumer or self._log_result
        self._incoming: queue.SimpleQueue[_PendingResult] = queue.SimpleQueue()
        self._pending: list[_PendingResult] = []
        self._copy_streams: dict[int, torch.cuda.Stream] = {}
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._worker: threading.Thread | None = None
        self._consumer_worker = threading.Thread(
            target=self._consume_results,
            daemon=True,
            name="inference-result-consumer",
        )
        self._consumer_worker.start()

    def submit(self, result: object, producer_stream: torch.cuda.Stream) -> None:
        """Schedule a CUDA-to-pinned-CPU copy and return without host synchronization."""
        if not isinstance(result, torch.Tensor) or not result.is_cuda:
            raise ValueError("inference_result must be a CUDA tensor")
        device_index = result.device.index
        if device_index is None:
            raise ValueError("inference_result must have a concrete CUDA device")

        with self._lock:
            copy_stream = self._copy_streams.setdefault(
                device_index, torch.cuda.Stream(device=device_index)
            )
            if self._worker is None:
                self._worker = threading.Thread(
                    target=self._publish_ready,
                    daemon=True,
                    name="inference-result-queue",
                )
                self._worker.start()

        dependency = torch.cuda.Event()
        with torch.cuda.stream(producer_stream):
            dependency.record()
        cpu_result = torch.empty_like(
            result,
            device="cpu",
            pin_memory=True,
            memory_format=torch.contiguous_format,
        )
        with torch.cuda.stream(copy_stream):
            copy_stream.wait_event(dependency)
            cpu_result.copy_(result, non_blocking=True)
            ready = torch.cuda.Event()
            ready.record(copy_stream)
        self._incoming.put(_PendingResult(cpu_result, ready, dependency))
        self._wake.set()

    def close(self) -> None:
        self._stop.set()
        self._wake.set()
        if self._worker is not None:
            self._worker.join(timeout=1)
        self._consumer_worker.join(timeout=1)

    @staticmethod
    def _log_result(result: torch.Tensor) -> None:
        """Default consumer keeps results observable until a sender is configured."""
        logger.debug("CPU inference result consumed: shape=%s", tuple(result.shape))

    @staticmethod
    def _put_latest(target: queue.Queue[torch.Tensor], result: torch.Tensor) -> None:
        try:
            target.put_nowait(result)
        except queue.Full:
            try:
                target.get_nowait()
                target.put_nowait(result)
            except (queue.Empty, queue.Full):
                pass

    def _publish_ready(self) -> None:
        while not self._stop.is_set():
            self._wake.wait(timeout=0.005)
            self._wake.clear()
            while True:
                try:
                    self._pending.append(self._incoming.get_nowait())
                except queue.Empty:
                    break
            still_pending: list[_PendingResult] = []
            for pending in self._pending:
                if pending.ready.query():
                    self._put_latest(self.cpu_queue, pending.cpu_result)
                else:
                    still_pending.append(pending)
            self._pending = still_pending

    def _consume_results(self) -> None:
        """Wait only in this daemon thread, never in the video pipeline thread."""
        while not self._stop.is_set():
            try:
                result = self.cpu_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                self._consumer(result)
            except Exception:
                logger.exception("Inference result consumer failed")
