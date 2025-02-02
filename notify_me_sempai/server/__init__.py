import asyncio
import logging
import os
from dataclasses import dataclass
import websockets
from websockets.asyncio.server import ServerConnection
import websockets.exceptions
from datetime import datetime, timezone
import json
import jwt

from notify_me_sempai.common import ServiceABC

logger = logging.getLogger(__name__)

__all__ = [
    "WsServerConfig", "WsServer", "ClientManager", "client_manager"
]

@dataclass(kw_only=True, slots=True)
class Client:
    username: str
    ws: ServerConnection

@dataclass(kw_only=True, slots=True)
class TokenData:
    username: str

class InvalidRequest(Exception):
    pass

class ClientManager:
    def __init__(self, secret: str):
        self.clients: dict[str, Client] = {}
        self.secret = secret

    def decode_token(self, token: str) -> TokenData:
        try:
            decoded_token = jwt.decode(token, self.secret, algorithms=["HS256"])
        except jwt.exceptions.InvalidSignatureError:
            raise InvalidRequest("invalid token provided")
        if not "username" in decoded_token:
            raise InvalidRequest("invalid token provided")
        return TokenData(
            username=decoded_token['username']
        )

    async def register(self, client: Client):
        async with asyncio.Lock():
            self.clients[client.username] = client

    async def unregister(self, client: Client):
        if client.username not in self.clients:
            return
        async with asyncio.Lock():
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
    

client_manager = ClientManager(secret=os.getenv("SECRET", "changeme"))

async def handler(websocket: ServerConnection):
    logger.info("new connection")
    if not websocket.request:
        logging.error("websocket have no request field")
        await websocket.close(reason="invalid request")
        return

    token = websocket.request.headers.get("token")
    if not token:
        await websocket.close(reason="token header is not provided")
        return

    try:
        token_data: TokenData = client_manager.decode_token(token)
    except InvalidRequest:
        await websocket.close(reason="invalid token provided")
        return

    client = Client(
        username=token_data.username,
        ws=websocket,
    )
    await client_manager.register(
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
        await client_manager.unregister(client)

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
