import asyncio
import logging
from dataclasses import dataclass

from notify_me_sempai.base import ServiceABC
from notify_me_sempai.server import client_manager

logger = logging.getLogger(__name__)

@dataclass(kw_only=True, slots=True)
class Message:
    target: str
    payload: str

class MessageDispatcher(ServiceABC):
    def __init__(self, q: asyncio.Queue):
        self.q = q
        self.manager = client_manager
        self.is_running = True
    
    async def setup(self):
        logger.info("message dispatcher is set")
    
    async def run(self):
        logger.info("message dispatcher is running")
        while self.is_running:
            new_message: Message = await self.q.get()
            if new_message.target == "":
                await self.manager.broadcast(new_message.payload)
            # TODO handle send to target user
        logger.info("message dispatcher is stoped")
    
    async def stop(self):
        self.is_running = False
        logger.info("stopping message dispatcher")