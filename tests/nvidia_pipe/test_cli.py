import unittest
import logging
import json
import os
import tempfile
from types import SimpleNamespace
from unittest import mock

import yaml

import nvidia_pipe.cli as cli
import nvidia_pipe.receive as receive_module
from nvidia_pipe.cli import (
    PIPELINE_NAME_FILTER,
    LiveParameters,
    callback_accepts_parameters,
    configure_pipeline_logging,
    validate_config,
)

class CliContractTests(unittest.TestCase):
    def valid(self):
        return {"name":"pipe-a","input":{"rtsp":{"url":"rtsp://in","transport":"tcp"}},"output":{"rtsp":{"url":"rtsp://out","transport":"tcp"}},"inference":{"gpuid":0,"interval_frames":1,"input_format":"native","frame_type":"pytorch","model":"model.py"}}
    def test_valid_config_passes(self):
        validate_config(self.valid())

    def test_parameter_aware_and_legacy_callbacks_are_detected(self):
        def aware(frame, infer, parameters):
            return frame

        def legacy(frame, infer):
            return frame

        self.assertTrue(callback_accepts_parameters(aware))
        self.assertFalse(callback_accepts_parameters(legacy))

    def test_live_parameters_reload_valid_yaml_and_keep_last_valid_values(self):
        original = self.valid()
        original["inference"]["parameters"] = {"font-size": 14}
        replacement = self.valid()
        replacement["inference"]["parameters"] = {"font-size": 28}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as file:
            yaml_path = file.name
            yaml.safe_dump(original, file)
        try:
            parameters = LiveParameters(yaml_path, original)
            self.assertEqual(parameters.refresh(), {"font-size": 14})
            with open(yaml_path, "w", encoding="utf-8") as file:
                yaml.safe_dump(replacement, file)
            stat = os.stat(yaml_path)
            os.utime(yaml_path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1))
            self.assertEqual(parameters.refresh(), {"font-size": 28})
            with open(yaml_path, "w", encoding="utf-8") as file:
                file.write("inference: [")
            stat = os.stat(yaml_path)
            os.utime(yaml_path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1))
            self.assertEqual(parameters.refresh(), {"font-size": 28})
        finally:
            os.unlink(yaml_path)
    def test_invalid_config_fails(self):
        with self.assertRaises(ValueError): validate_config({})
        config = self.valid(); config["inference"]["interval_frames"] = -1
        with self.assertRaises(ValueError): validate_config(config)

    def test_missing_or_empty_name_fails(self):
        for name in (None, "", "   "):
            config = self.valid()
            if name is None:
                del config["name"]
            else:
                config["name"] = name
            with self.assertRaises(ValueError):
                validate_config(config)

    def test_configure_pipeline_logging_injects_config_name(self):
        configure_pipeline_logging("pipe-a")
        record = logging.makeLogRecord({"msg": "test"})

        PIPELINE_NAME_FILTER.filter(record)

        self.assertEqual(record.pipeline_name, "pipe-a")

    def test_pipeline_tracks_received_sent_and_inference_outcomes(self):
        first_frame = object()
        second_frame = object()
        packet = mock.Mock(codec="h264", packet_data=b"encoded")
        submitted_packets = []

        class FakeSender:
            def __init__(self, *args, **kwargs):
                pass

            def start(self):
                pass

            def submit(self, submitted_packet):
                submitted_packets.append(submitted_packet)

        model = mock.Mock()
        model.on_frame.side_effect = [first_frame, RuntimeError("inference failed")]

        def fake_encode(frames, **kwargs):
            self.assertEqual(list(frames), [first_frame, second_frame])
            return [packet, packet]

        with (
            mock.patch.object(cli, "load_config", return_value=self.valid()),
            mock.patch.object(cli, "configure_cuda_dll_path"),
            mock.patch.object(cli, "load_module", return_value=model),
            mock.patch.object(cli, "Sender", FakeSender),
            mock.patch.object(cli, "receive", return_value=object()),
            mock.patch.object(cli, "decode", return_value=[first_frame, second_frame]),
            mock.patch.object(cli, "encode", side_effect=fake_encode),
            mock.patch.object(cli, "replace", side_effect=lambda value, **_: value),
            mock.patch.object(cli, "is_idr_keyframe", return_value=False),
            mock.patch.object(cli, "torch"),
        ):
            cli.run_pipeline("pipeline.yml")

        self.assertEqual(cli.received_frame_count, 2)
        self.assertEqual(cli.sent_frame_count, 2)
        self.assertEqual(cli.inference_success_frame_count, 1)
        self.assertEqual(cli.inference_failure_frame_count, 1)
        self.assertEqual(receive_module.out_of_order_frame_count, 0)
        self.assertEqual(len(submitted_packets), 2)
        self.assertEqual(model.on_frame.call_args.kwargs["parameters"], {})

    def test_send_frame_statistics_posts_all_counters(self):
        cli.received_frame_count = 8
        cli.sent_frame_count = 7
        cli.inference_success_frame_count = 6
        cli.inference_failure_frame_count = 1
        receive_module.out_of_order_frame_count = 0
        receive_module.input_rtsp_status = "connected"
        cli.sender = SimpleNamespace(connection_status="disconnected")

        response = mock.MagicMock()
        response.__enter__.return_value = response
        with mock.patch.object(cli, "urlopen", return_value=response) as urlopen_mock:
            cli.send_frame_statistics("http://127.0.0.1:8080/api/pipelines/camera-a/statistics")

        request = urlopen_mock.call_args.args[0]
        self.assertEqual(request.method, "POST")
        self.assertEqual(
            json.loads(request.data),
            {
                "received_frame_count": 8,
                "sent_frame_count": 7,
                "inference_success_frame_count": 6,
                "inference_failure_frame_count": 1,
                "out_of_order_frame_count": 0,
                "input_rtsp_status": "connected",
                "output_rtsp_status": "disconnected",
            },
        )

if __name__ == "__main__":
    unittest.main()
