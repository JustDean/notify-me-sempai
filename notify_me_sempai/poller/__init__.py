import json
import logging
import asyncio
import aio_pika
from dataclasses import dataclass

from notify_me_sempai.common import ServiceABC
from notify_me_sempai.dispatcher import Message

logger = logging.getLogger(__name__)

@dataclass
class PollerConfig:
    host: str = "localhost"
    port: int = 5672
    login: str = "guest"
    password: str = "guest"
    virtualhost: str = "/"
    queue_name: str = "default"


class Poller(ServiceABC):
    def __init__(self, config: PollerConfig, queue: asyncio.Queue):
        self.config = config
        self._q = queue
        self._conn: aio_pika.Connection | None = None
        self._chanel: aio_pika.Channel | None = None
        self._broker_q: aio_pika.Queue | None = None
        self._isrunning = True
    
    async def setup(self):
        self._conn = await aio_pika.connect(
            host=self.config.host,
            port=self.config.port,
            login=self.config.login,
            password=self.config.password,
            virtualhost=self.config.virtualhost,
        )
        self._chanel = await self._conn.channel()
        self._broker_q = await self._chanel.get_queue(
            self.config.queue_name,
        )
        logger.info("poller is set")
    
    async def run(self):
        logger.info("running poller")
        try:
            async with self._broker_q.iterator() as q_iter:
                async for message in q_iter:
                    logger.debug("New message is received")
                    async with message.process():
                        try:
                            unprocessed_message = message.body.decode()
                            processed_message = json.loads(unprocessed_message)
                            await self._q.put(
                                Message(
                                    target=processed_message['target'],
                                    payload=processed_message['payload']
                                )
                            )
                        except Exception as err:
                            logger.warning(f"Unable to process message {message}: {err}")
                    if not self._isrunning:
                        break
        except asyncio.CancelledError:
            logger.info("stopping poller")
        
    async def stop(self):
        self._isrunning = False
        await self._chanel.close()
        await self._conn.close()
        logger.info("poller is stoped gracefully")