from abc import ABC, abstractmethod


class DependencyScope(ABC):
    async def __aenter__(self) -> 'DependencyScope':
        return self

    async def __aexit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None,
                        exc_tb: object | None) -> None:
        await self.close()

    @abstractmethod
    async def resolve[T](self, t: type[T], **kwargs) -> T:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass

    @abstractmethod
    def scope(self) -> 'DependencyScope':
        pass
