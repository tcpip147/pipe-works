import unittest
import logging

from nvidia_pipe.cli import PIPELINE_NAME_FILTER, configure_pipeline_logging, validate_config

class CliContractTests(unittest.TestCase):
    def valid(self):
        return {"name":"pipe-a","input":{"rtsp":{"url":"rtsp://in","transport":"tcp"}},"output":{"rtsp":{"url":"rtsp://out","transport":"tcp"}},"inference":{"gpuid":0,"interval_frames":1,"input_format":"native","frame_type":"pytorch","model":"model.py"}}
    def test_valid_config_passes(self):
        validate_config(self.valid())
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

if __name__ == "__main__":
    unittest.main()
