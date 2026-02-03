from abc import ABC, abstractmethod


class DependencyScope(ABC):
    @abstractmethod
    async def resolve[T](self, t: type[T], **kwargs) -> T:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass

    @abstractmethod
    def scope(self) -> 'DependencyScope':
        pass
