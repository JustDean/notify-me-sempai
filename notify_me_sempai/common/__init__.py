from typing import Coroutine
from abc import ABC, abstractmethod


class ServiceABC(ABC):
    @abstractmethod
    async def setup(self) -> Coroutine[None, None, None]:
        raise NotImplemented

    @abstractmethod
    async def run(self) -> Coroutine[None, None, None]:
        raise NotImplemented

    @abstractmethod
    async def stop(self) -> Coroutine[None, None, None]:
        raise NotImplemented