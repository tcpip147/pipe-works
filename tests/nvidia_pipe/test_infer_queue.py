import queue
import threading
import unittest

import torch

from nvidia_pipe.infer_queue import InferenceResultQueue


class InferenceResultQueueTests(unittest.TestCase):
    def test_consumer_thread_receives_cpu_results_without_blocking_the_caller(self):
        consumed = []
        consumed_event = threading.Event()

        def consumer(result):
            consumed.append(result)
            consumed_event.set()

        dispatcher = InferenceResultQueue(consumer=consumer)
        result = torch.tensor([[1.0, 2.0, 3.0, 4.0]])
        try:
            InferenceResultQueue._put_latest(dispatcher.cpu_queue, result)

            self.assertTrue(consumed_event.wait(timeout=1))
            self.assertIs(consumed[0], result)
        finally:
            dispatcher.close()

    def test_submit_rejects_a_non_cuda_result(self):
        dispatcher = InferenceResultQueue()
        with self.assertRaisesRegex(ValueError, "CUDA tensor"):
            dispatcher.submit(torch.zeros((1, 4)), object())

    def test_latest_result_replaces_the_oldest_when_queue_is_full(self):
        target: queue.Queue[torch.Tensor] = queue.Queue(maxsize=1)
        first = torch.tensor([[1.0, 2.0, 3.0, 4.0]])
        latest = torch.tensor([[5.0, 6.0, 7.0, 8.0]])
        target.put(first)

        InferenceResultQueue._put_latest(target, latest)

        self.assertTrue(torch.equal(target.get_nowait(), latest))
