import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from unittest import mock

from plumber.cli import PipelineManager, make_handler


class PipelineManagerTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        root = Path(self.directory.name)
        (root / "pipe.yml").write_text("name: camera-a\n", encoding="utf-8")
        (root / "plumber.yml").write_text(
            "port: 18080\npipelines:\n  - config: pipe.yml\n", encoding="utf-8"
        )
        self.manager = PipelineManager(root / "plumber.yml")

    def tearDown(self):
        self.directory.cleanup()

    def test_lists_configured_pipeline_as_stopped(self):
        self.assertEqual(self.manager.list()[0]["state"], "stopped")
        self.assertEqual(self.manager.port, 18080)
        statistics = self.manager.list()[0]["statistics"]
        self.assertEqual(statistics["input_rtsp_status"], "disconnected")
        self.assertEqual(statistics["output_rtsp_status"], "disconnected")
        self.assertFalse(self.manager.auto_start)

    def test_auto_start_starts_all_pipelines_only_when_enabled(self):
        with mock.patch.object(self.manager, "start_all", return_value=[]) as start_all:
            self.assertEqual(self.manager.start_configured_pipelines(), [])
        start_all.assert_not_called()

        config_path = Path(self.directory.name) / "plumber.yml"
        config_path.write_text(
            "port: 18080\nauto_start: true\npipelines:\n  - config: pipe.yml\n",
            encoding="utf-8",
        )
        enabled = PipelineManager(config_path)
        with mock.patch.object(enabled, "start_all", return_value=[{"name": "camera-a"}]) as start_all:
            self.assertEqual(enabled.start_configured_pipelines(), [{"name": "camera-a"}])
        start_all.assert_called_once()

    def test_auto_start_requires_a_boolean(self):
        config_path = Path(self.directory.name) / "plumber.yml"
        config_path.write_text(
            "port: 18080\nauto_start: enabled\npipelines:\n  - config: pipe.yml\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "auto_start"):
            PipelineManager(config_path)

    def test_unknown_pipeline_is_rejected(self):
        with self.assertRaises(KeyError):
            self.manager.start("missing")

    def test_start_creates_child_process(self):
        process = mock.Mock(pid=123, exitcode=None)
        process.is_alive.return_value = True
        with mock.patch.object(
            self.manager._context, "Process", return_value=process
        ) as process_factory:
            result = self.manager.start("camera-a")
        process.start.assert_called_once()
        self.assertEqual(
            process_factory.call_args.kwargs["args"][1],
            "http://127.0.0.1:18080/api/pipelines/camera-a/statistics",
        )
        self.assertEqual(result["state"], "running")

    def test_start_all_starts_every_configured_pipeline(self):
        process = mock.Mock(pid=123, exitcode=None)
        process.is_alive.return_value = True
        with mock.patch.object(
            self.manager._context, "Process", return_value=process
        ) as process_factory:
            result = self.manager.start_all()
        self.assertEqual([item["name"] for item in result], ["camera-a"])
        process_factory.assert_called_once()

    def test_http_api_lists_pipelines_and_rejects_unknown_name(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.manager))
        thread = Thread(target=server.serve_forever)
        thread.start()
        try:
            base_url = f"http://127.0.0.1:{server.server_port}"
            with urlopen(f"{base_url}/api/pipelines") as response:
                self.assertIn(b'"camera-a"', response.read())
            request = Request(f"{base_url}/api/pipelines/start-all", method="POST")
            with mock.patch.object(self.manager, "start_all", return_value=[]) as start_all:
                with urlopen(request) as response:
                    self.assertEqual(json.load(response), [])
            start_all.assert_called_once()
            with urlopen(f"{base_url}/") as response:
                page = response.read()
            self.assertIn(b"RTSP pipeline control", page)
            self.assertIn(b"start-all", page)
            self.assertIn(b"function startAll", page)
            self.assertIn(b"Inference Failed", page)
            self.assertIn(b"endpoint-statuses", page)
            self.assertIn(b"Input: ", page)
            self.assertIn(b"Output: ", page)
            self.assertIn(b"markConnectionsDisconnected", page)
            self.assertIn(b"Pipeline status request failed", page)
            self.assertIn(b'card.classList.remove("is-running")', page)
            self.assertIn(b'textContent = "stopped"', page)
            self.assertIn(b"function updatePipelineCard", page)
            self.assertIn(b'if (!isRunning)', page)
            self.assertNotIn(b'innerHTML = pipelines.length', page)
            with self.assertRaisesRegex(Exception, "404"):
                urlopen(f"{base_url}/api/pipelines/missing")
            request = Request(
                f"{base_url}/api/pipelines/camera-a/statistics",
                data=json.dumps(
                    {
                        "received_frame_count": 2,
                        "sent_frame_count": 2,
                        "inference_success_frame_count": 1,
                        "inference_failure_frame_count": 1,
                        "out_of_order_frame_count": 3,
                        "input_rtsp_status": "connected",
                        "output_rtsp_status": "disconnected",
                    }
                ).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(request) as response:
                statistics = json.load(response)["statistics"]
            self.assertEqual(statistics["received_frame_count"], 2)
            self.assertEqual(statistics["inference_failure_frame_count"], 1)
            self.assertEqual(statistics["out_of_order_frame_count"], 3)
            self.assertEqual(statistics["input_rtsp_status"], "connected")
            self.assertEqual(statistics["output_rtsp_status"], "disconnected")

            invalid_request = Request(
                f"{base_url}/api/pipelines/camera-a/statistics",
                data=json.dumps(
                    {
                        **statistics,
                        "output_rtsp_status": "invalid",
                    }
                ).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with self.assertRaises(HTTPError) as error:
                urlopen(invalid_request)
            self.assertEqual(error.exception.code, 400)
            self.assertEqual(
                self.manager.status("camera-a")["statistics"]["output_rtsp_status"],
                "disconnected",
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()
