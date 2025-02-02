import asyncio
import logging

from notify_me_sempai.poller import Poller, PollerConfig
from notify_me_sempai.server import WsServer, WsServerConfig
from notify_me_sempai.dispatcher import Message, MessageDispatcher
from notify_me_sempai.common import ServiceABC

logger = logging.getLogger("main")


async def main():
    logging.basicConfig(level=logging.INFO)
    queue = asyncio.Queue[Message](100)
    services: list[ServiceABC] = [
        Poller(PollerConfig(), queue),
        MessageDispatcher(queue),
        WsServer(WsServerConfig())
    ]
    try:
        logger.info("starting")
        await asyncio.gather(*[s.setup() for s in services])
        await asyncio.gather(*[s.run() for s in services])
    except asyncio.CancelledError:
        logger.info("stopping")
        await asyncio.gather(*[s.stop() for s in services])
    except Exception as err:
        logger.error(f"unhandled error: {err}")
    finally:
        logger.info("shutting down")


if __name__ == "__main__":
    asyncio.run(main())