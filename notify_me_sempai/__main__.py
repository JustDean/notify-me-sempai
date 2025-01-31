import asyncio
import logging

from notify_me_sempai.poller import Poller, PollerConfig
from notify_me_sempai.server import WsServer, WsServerConfig
from notify_me_sempai.dispatcher import Message, MessageDispatcher


logger = logging.getLogger("main")


async def main():
    logging.basicConfig(level=logging.INFO)
    queue = asyncio.Queue[Message](100)
    poller = Poller(PollerConfig(), queue)
    dispatcher = MessageDispatcher(queue)
    ws_server = WsServer(WsServerConfig())
    try:
        logger.info("starting")
        await asyncio.gather(poller.setup(), dispatcher.setup(), ws_server.setup())
        await asyncio.gather(poller.run(), dispatcher.run(), ws_server.run())
    except asyncio.CancelledError:
        logger.info("stopping")
        await asyncio.gather(poller.stop(), dispatcher.stop(), ws_server.stop())
    except Exception as err:
        logger.error(f"unhandled error: {err}")
    finally:
        logger.info("shutting down")


if __name__ == "__main__":
    asyncio.run(main())