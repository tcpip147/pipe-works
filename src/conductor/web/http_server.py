import uvicorn
from pathlib import Path
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, ConfigDict
from typing import Literal
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import logging
from conductor.process.supervisor import (
    Supervisor,
    ProcessAlreadyExistsError,
    InvalidProcessError,
    ProcessNotFoundError,
    ProcessNotRunningError,
)
from conductor.web.process_event_broker import ProcessEventBroker

logger = logging.getLogger(__name__)


class CreateProcessRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1)
    desired_state: bool = False
    input_rtsp_url: str = Field(min_length=1)
    input_transport: Literal["tcp", "udp"]
    jitter_buffer: int = Field(ge=0)
    output_rtsp_url: str = Field(min_length=1)
    output_transport: Literal["tcp", "udp"]
    metadata_enabled: bool
    metadata_module: str = ""
    inference_enabled: bool
    gpuid: int = Field(ge=0)
    interval_frames: int = Field(ge=0)
    input_format: Literal["native", "rgb", "rgbp"]
    frame_type: Literal["pytorch"]
    inference_module: str = ""
    postprocess_enabled: bool
    postprocess_module: str = ""
    sequence: int = Field(default=0, ge=0)


class HttpServer:
    def __init__(self, port: int, supervisor: Supervisor) -> None:
        self._port = port
        self._supervisor = supervisor
        self._events = ProcessEventBroker()
        self._supervisor.setEventPublisher(self._events.publish)
        self._supervisor.setStatusPublisher(self._events.publishStatus)
        self._web_root = Path(__file__).parent
        self._app = FastAPI(title="Conductor")
        self._app.mount(
            "/static",
            StaticFiles(directory=self._web_root / "static"),
            name="static",
        )

        self._register_routes()

    def run(self) -> None:
        uvicorn.run(
            self._app,
            port=self._port,
            reload=False,
        )

    def _register_routes(self) -> None:
        @self._app.get("/", include_in_schema=False)
        def index() -> FileResponse:
            return FileResponse(self._web_root / "index.html")

        @self._app.get("/api/processes")
        def getProcesses():
            return self._supervisor.getProcesses()

        @self._app.websocket("/ws/processes/{process_id}/logs")
        async def processLogs(websocket: WebSocket, process_id: str) -> None:
            await websocket.accept()
            event_queue = self._events.subscribe(process_id)
            try:
                while True:
                    event = await event_queue.get()
                    await websocket.send_json(event)
            except WebSocketDisconnect:
                pass
            finally:
                self._events.unsubscribe(process_id, event_queue)

        @self._app.websocket("/ws/processes/status")
        async def processStatus(websocket: WebSocket) -> None:
            await websocket.accept()
            event_queue = self._events.subscribeStatus()
            try:
                while True:
                    event = await event_queue.get()
                    await websocket.send_json(event)
            except WebSocketDisconnect:
                pass
            finally:
                self._events.unsubscribeStatus(event_queue)

        @self._app.post("/api/processes", status_code=201)
        def addProcess(process: CreateProcessRequest):
            try:
                self._supervisor.addProcess(process.model_dump())
            except ProcessAlreadyExistsError as error:
                raise HTTPException(409, str(error)) from error
            except InvalidProcessError as error:
                raise HTTPException(422, str(error)) from error
            return {"id": process.name}

        @self._app.post("/api/processes/start", status_code=202)
        def startProcess(process_id: str):
            try:
                self._supervisor.startProcess(process_id)
            except ProcessNotFoundError as error:
                raise HTTPException(404, str(error)) from error
            return {"id": process_id}

        @self._app.post("/api/processes/stop", status_code=202)
        def stopProcess(process_id: str):
            try:
                self._supervisor.stopProcess(process_id)
            except ProcessNotFoundError as error:
                raise HTTPException(404, str(error)) from error
            except ProcessNotRunningError as error:
                raise HTTPException(409, str(error)) from error
            return {"id": process_id}

        @self._app.put("/api/processes")
        def updateProcess(process_id: str, process: CreateProcessRequest):
            if process.name != process_id:
                raise HTTPException(422, "Process Name은 변경할 수 없습니다.")
            try:
                self._supervisor.updateProcess(process_id, process.model_dump())
            except ProcessNotFoundError as error:
                raise HTTPException(404, str(error)) from error
            except InvalidProcessError as error:
                raise HTTPException(422, str(error)) from error
            return {"id": process_id}

        @self._app.delete("/api/processes", status_code=204)
        def deleteProcess(process_id: str) -> None:
            try:
                self._supervisor.deleteProcess(process_id)
            except ProcessNotFoundError as error:
                raise HTTPException(404, str(error)) from error
