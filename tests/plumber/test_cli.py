import unittest
from unittest import mock
from pathlib import Path

from plumber.cli import resolve_pipeline_configs, stop_processes

class PlumberTests(unittest.TestCase):
    def test_stop_processes_terminates_and_reaps_children(self):
        process = mock.Mock(); process.is_alive.side_effect = [True, False]; process.pid = 1
        stop_processes([process])
        process.terminate.assert_called_once(); process.join.assert_called_once_with(timeout=3)

    @mock.patch("plumber.cli.load_config")
    def test_resolve_pipeline_configs_reads_name_from_pipe_config(self, load_config):
        load_config.side_effect = [{"name": "camera-a"}, {"name": "camera-b"}]
        resolved = resolve_pipeline_configs(
            Path("C:/configs/plumber.yml"),
            [{"config": "pipe-a.yml"}, {"config": "pipe-b.yml"}],
        )
        self.assertEqual([name for name, _ in resolved], ["camera-a", "camera-b"])
        self.assertEqual([path.name for _, path in resolved], ["pipe-a.yml", "pipe-b.yml"])

    @mock.patch("plumber.cli.load_config")
    def test_resolve_pipeline_configs_rejects_duplicate_names_before_start(self, load_config):
        load_config.side_effect = [{"name": "camera"}, {"name": "camera"}]
        with self.assertRaisesRegex(ValueError, "Duplicate pipeline name"):
            resolve_pipeline_configs(
                Path("C:/configs/plumber.yml"),
                [{"config": "pipe-a.yml"}, {"config": "pipe-b.yml"}],
            )

if __name__ == "__main__": unittest.main()
