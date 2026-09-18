import uvicorn
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import logging

logger = logging.getLogger(__name__)


class HttpServer:
    def __init__(self, port: int):
        self._port = port
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
        self._app.get("/", include_in_schema=False)(self._index)

    def _index(self) -> FileResponse:
        return FileResponse(self._web_root / "index.html")
