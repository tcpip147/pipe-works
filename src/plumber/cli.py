from pathlib import Path
from typing import Any

import logging
import argparse
import multiprocessing as mp
import yaml

from nvidia_pipe.cli import run_pipeline_entry

logger = logging.getLogger(__name__)


def load_config(path: str) -> dict[str, Any]:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="NVIDIA video pipeline")
    parser.add_argument(
        "-c",
        "--config",
        default="plumber.yml",
        help="YAML 설정 파일 경로",
    )
    return parser.parse_args()


def stop_processes(processes: list[mp.Process]) -> None:
    for process in processes:
        if process.is_alive():
            logger.info("Stopping %s (pid=%s)", process.name, process.pid)
            process.terminate()

    for process in processes:
        if process.pid is not None:
            process.join(timeout=3)

    for process in processes:
        if process.is_alive():
            logger.warning(
                "Killing unresponsive %s (pid=%s)", process.name, process.pid
            )
            process.kill()
            process.join(timeout=2)
            if process.is_alive():
                logger.error("Could not reap %s after kill request", process.name)


def resolve_pipeline_configs(
    plumber_path: Path, pipelines: list[dict[str, Any]]
) -> list[tuple[str, Path]]:
    """Resolve child configuration paths and their required, unique names."""
    resolved: list[tuple[str, Path]] = []
    names: set[str] = set()

    for index, pipeline in enumerate(pipelines, start=1):
        config_value = pipeline.get("config") if isinstance(pipeline, dict) else None
        if not isinstance(config_value, str) or not config_value:
            raise ValueError(f"Pipeline {index} requires a configuration file path")

        pipeline_path = (plumber_path.parent / config_value).resolve()
        pipeline_config = load_config(str(pipeline_path))
        name = pipeline_config.get("name") if isinstance(pipeline_config, dict) else None
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Pipeline configuration requires a non-empty name: {pipeline_path}")

        name = name.strip()
        if name in names:
            raise ValueError(f"Duplicate pipeline name: {name}")
        names.add(name)
        resolved.append((name, pipeline_path))

    return resolved


def run_pipelines(config_path: str | Path | None = None) -> None:
    plumber_path = Path(config_path or "plumber.yml").resolve()
    pipelines = load_config(str(plumber_path))["pipelines"]
    pipeline_configs = resolve_pipeline_configs(plumber_path, pipelines)
    context = mp.get_context("spawn")
    processes: list[mp.Process] = []
    started_processes: list[mp.Process] = []

    for name, pipeline_path in pipeline_configs:
        process = context.Process(
            target=run_pipeline_entry,
            args=(str(pipeline_path),),
            name=name,
        )
        processes.append(process)

    try:
        for process in processes:
            process.start()
            started_processes.append(process)

        for process in started_processes:
            process.join()

        failed = [p for p in processes if p.exitcode not in (0, None)]
        if failed:
            raise RuntimeError(
                f"다음 파이프라인이 실패했습니다: {[p.name for p in failed]}"
            )
    finally:
        stop_processes(processes)


def run_pipelines_entry(config_path: str | Path | None = None) -> None:
    try:
        run_pipelines(config_path)
    except KeyboardInterrupt:
        logger.info("사용자 요청으로 종료합니다.")


def main() -> None:
    args = parse_args()
    run_pipelines_entry(args.config)


if __name__ == "__main__":
    main()
