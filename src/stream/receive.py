import logging
import threading
from collections.abc import Iterator
from typing import Any

import av


logger = logging.getLogger(__name__)

RECONNECT_DELAY_SECONDS = 3.0


def receive(arguments: Any, stop_event: threading.Event) -> Iterator[av.Packet]:
    while not stop_event.is_set():
        container = None
        try:
            logger.info("Opening RTSP input: %s", arguments.input_rtsp_url)
            container = av.open(
                arguments.input_rtsp_url,
                mode="r",
                options={"rtsp_transport": arguments.input_transport},
                timeout=(5.0, 5.0),
            )

            for packet in container.demux(video=0):
                if stop_event.is_set():
                    return
                if packet:
                    yield packet
        except (av.FFmpegError, OSError) as error:
            if not stop_event.is_set():
                logger.warning("RTSP input disconnected: %s", error)
        finally:
            if container is not None:
                container.close()

        if not stop_event.is_set():
            logger.info("Retrying RTSP input in %.0f seconds.", RECONNECT_DELAY_SECONDS)
            stop_event.wait(RECONNECT_DELAY_SECONDS)
