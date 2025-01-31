from abc import ABC, abstractmethod


class ServiceABC(ABC):
    @abstractmethod
    async def setup(self):
        raise NotImplemented

    @abstractmethod
    async def run(self):
        raise NotImplemented

    @abstractmethod
    async def stop(self):
        raise NotImplemented