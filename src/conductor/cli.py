from conductor.web.http_server import HttpServer
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(name)s][%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)


def main() -> None:
    HttpServer(8900).run()


if __name__ == "__main__":
    main()
