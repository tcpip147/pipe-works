# src/conductor/storage/process_repository.py
import sqlite3
from contextlib import contextmanager
from collections.abc import Generator
from pathlib import Path
from typing import Any

database_path = Path(__file__).resolve().parent / "process.db"
LATEST_SCHEMA_VERSION = 1


class ProcessRepository:
    def __init__(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            self._migrate(connection)

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        connection = sqlite3.connect(database_path)
        try:
            connection.row_factory = sqlite3.Row
            with connection:
                yield connection
        finally:
            connection.close()

    def _migrate(self, connection: sqlite3.Connection) -> None:
        current_version = connection.execute("PRAGMA user_version").fetchone()[0]
        migrations = {
            1: self._migrate_v1,
        }
        while current_version < LATEST_SCHEMA_VERSION:
            next_version = current_version + 1

            with connection:
                connection.execute("BEGIN")
                migrations[next_version](connection)
                connection.execute(f"PRAGMA user_version = {next_version}")

            current_version = next_version

    def get(self, process_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM processes WHERE id = ?",
                (process_id,),
            ).fetchone()

            return dict(row) if row is not None else None

    def getAll(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM processes ORDER BY sequence"
            ).fetchall()

            return [dict(row) for row in rows]

    def add(self, process: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO processes (
                    id,
                    input_rtsp_url,
                    input_transport,
                    input_jitter_buffer,
                    output_rtsp_url,
                    output_transport,
                    metadata_enabled,
                    metadata_module_path,
                    inference_enabled,
                    inference_gpuid,
                    inference_interval_frames,
                    inference_input_format,
                    inference_frame_type,
                    inference_module_path,
                    postprocess_enabled,
                    postprocess_module_path,
                    desired_state,
                    sequence
                ) VALUES (
                    :id,
                    :input_rtsp_url,
                    :input_transport,
                    :input_jitter_buffer,
                    :output_rtsp_url,
                    :output_transport,
                    :metadata_enabled,
                    :metadata_module_path,
                    :inference_enabled,
                    :inference_gpuid,
                    :inference_interval_frames,
                    :inference_input_format,
                    :inference_frame_type,
                    :inference_module_path,
                    :postprocess_enabled,
                    :postprocess_module_path,
                    :desired_state,
                    :sequence
                )
                """,
                process,
            )

    def delete(self, process_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM processes WHERE id = ?",
                (process_id,),
            )
            return cursor.rowcount > 0

    def update(self, process_id: str, process: dict[str, Any]) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE processes SET
                    input_rtsp_url = :input_rtsp_url,
                    input_transport = :input_transport,
                    input_jitter_buffer = :input_jitter_buffer,
                    output_rtsp_url = :output_rtsp_url,
                    output_transport = :output_transport,
                    metadata_enabled = :metadata_enabled,
                    metadata_module_path = :metadata_module_path,
                    inference_enabled = :inference_enabled,
                    inference_gpuid = :inference_gpuid,
                    inference_interval_frames = :inference_interval_frames,
                    inference_input_format = :inference_input_format,
                    inference_frame_type = :inference_frame_type,
                    inference_module_path = :inference_module_path,
                    postprocess_enabled = :postprocess_enabled,
                    postprocess_module_path = :postprocess_module_path,
                    desired_state = :desired_state,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :process_id
                """,
                {**process, "process_id": process_id},
            )
            return cursor.rowcount > 0

    def _migrate_v1(self, connection: sqlite3.Connection) -> None:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS processes (
                id TEXT PRIMARY KEY,
                input_rtsp_url TEXT NOT NULL,
                input_transport TEXT NOT NULL CHECK (input_transport IN ('tcp', 'udp')),
                input_jitter_buffer INTEGER NOT NULL DEFAULT 30 CHECK (input_jitter_buffer >= 0),
                output_rtsp_url TEXT NOT NULL,
                output_transport TEXT NOT NULL CHECK (output_transport IN ('tcp', 'udp')),
                metadata_enabled INTEGER NOT NULL DEFAULT 0 CHECK (metadata_enabled IN (0, 1)),
                metadata_module_path TEXT,
                inference_enabled INTEGER NOT NULL DEFAULT 1 CHECK (inference_enabled IN (0, 1)),
                inference_gpuid INTEGER NOT NULL DEFAULT 0 CHECK (inference_gpuid >= 0),
                inference_interval_frames INTEGER NOT NULL DEFAULT 1 CHECK (inference_interval_frames >= 0),
                inference_input_format TEXT NOT NULL DEFAULT 'native' CHECK (inference_input_format IN ('native', 'rgb', 'rgbp')),
                inference_frame_type TEXT NOT NULL DEFAULT 'pytorch' CHECK (inference_frame_type IN ('pytorch')),
                inference_module_path TEXT,
                postprocess_enabled INTEGER NOT NULL DEFAULT 1 CHECK (postprocess_enabled IN (0, 1)),
                postprocess_module_path TEXT,
                desired_state TEXT NOT NULL DEFAULT 'stopped' CHECK (desired_state IN ('running', 'stopped')),
                sequence INTEGER NOT NULL DEFAULT 0 CHECK (sequence >= 0),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
