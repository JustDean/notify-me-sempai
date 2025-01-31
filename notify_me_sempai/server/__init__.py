import asyncio
import logging
from dataclasses import dataclass
import websockets
from websockets.asyncio.server import ServerConnection
import websockets.exceptions
from datetime import datetime, timezone
import json

from notify_me_sempai.common import ServiceABC

logger = logging.getLogger(__name__)

__all__ = [
    "WsServerConfig", "WsServer", "ClientManager", "client_manager"
]

@dataclass(kw_only=True, slots=True)
class Client:
    username: str
    ws: ServerConnection

class ClientManager:
    def __init__(self):
        self.clients: dict[str, Client] = {}
    
    def register(self, client: Client):
        self.clients[client.username] = client

    def unregister(self, client: Client):
        self.clients.pop(client.username)

    @staticmethod
    def compose_message(payload: str) -> str:
        message = {
            "dt": datetime.now(timezone.utc).isoformat(),
            "payload": payload
        }
        return json.dumps(message)
    
    async def broadcast(self, payload: str):
        tasks = []
        for cli in self.clients.values():
            tasks.append(
                cli.ws.send(self.compose_message(payload), text=True)
            )
        await asyncio.gather(*tasks)
    
    async def target_send(self, payload: str, username: str):
        client = self.clients.get(username)
        if not client:
            logger.warning(f"Cant's send message {payload} to client {username}. Client is not connected to server")
            return
        await client.ws.send(self.compose_message(payload), text=True)
    
    async def close_all_connections(self):
        tasks = []
        for cli in self.clients.values():
            tasks.append(cli.ws.close())
        await asyncio.gather(*tasks)
    

client_manager = ClientManager()

async def handler(websocket: ServerConnection):
    logger.info("new connection")
    if not websocket.request:
        logging.error("websocket have no request field")
        await websocket.close(reason="username header is not provided")
        return
    
    username = websocket.request.headers.get("username")
    if not username:
        await websocket.close(reason="username header is not provided")
        return
    client = Client(
        username=username,
        ws=websocket,
    )
    client_manager.register(
        client
    )
    try:
        async for message in websocket:
            logger.info(f"Client {client.username} says {str(message)}")
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"client {client.username} connection close")
    except Exception as err:
        logger.error(f"Connection was not closed properly {err}")
    finally:
        client_manager.unregister(client)

@dataclass
class WsServerConfig:
    host: str = 'localhost'
    port: int = 8765


class WsServer(ServiceABC):
    def __init__(self, config: WsServerConfig):
        self.config = config
        self._server: websockets.Server | None = None
    
    async def setup(self):
        self._server = websockets.serve(handler, self.config.host, self.config.port)
        logger.info("ws server is set")

    async def run(self):
        logger.info("ws is running...")
        async with self._server as server:
            await server.serve_forever()
        
    async def stop(self):
        logger.info("ws server is stopped gracefully")
        await client_manager.close_all_connections()
