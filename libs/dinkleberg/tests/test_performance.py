import asyncio
import logging

import pytest
import time

from dinkleberg import DependencyConfigurator
from dinkleberg_abc import Dependency

logger = logging.getLogger(__name__)


class Database:
    pass


class Cache[T]:
    def __init__(self, t: type[T]):
        self.t = t


class UserRepository:
    def __init__(self, db: Database, cache: Cache[str]):
        self.db = db
        self.cache = cache


class EmailService:
    def __init__(self):
        self.sent_count = 0

    async def send(self, msg: str):
        # Simulate slight IO delay to test gather overhead
        # await asyncio.sleep(0.0001)
        self.sent_count += 1


class UserService:
    def __init__(self, repo: UserRepository, email: EmailService):
        self.repo = repo
        self.email = email

    # Method Injection Test
    async def activate_user(self, user_id: str,
                            email_service: EmailService = Dependency()):
        await email_service.send(f"Welcome {user_id}")
        return True


# --- The Benchmark ---

@pytest.fixture
def container():
    di = DependencyConfigurator()

    # 1. Register Singleton (Fast path)
    di.add_singleton(t=Database, instance=Database())
    di.add_singleton(t=EmailService, instance=EmailService())

    # 2. Register Generic Transient (Logic heavy)
    di.add_transient(t=Cache)

    # 3. Register Standard Transients (Introspection heavy)
    di.add_transient(t=UserRepository)
    di.add_transient(t=UserService)

    return di


@pytest.mark.asyncio
async def test_performance_resolve_throughput(container):
    """
    Measures pure resolution speed manually to avoid event loop conflicts.
    """
    # 1. Warmup (optional but good for stability)
    for _ in range(100):
        await container.resolve(UserService)

    # 2. Measure
    start = time.perf_counter()
    ops = 5_000

    for _ in range(ops):
        service = await container.resolve(UserService)
        # Verify correctness (cheap checks)
        assert isinstance(service.repo.cache, Cache)
        assert service.repo.cache.t is str

    duration = time.perf_counter() - start
    ops_per_sec = ops / duration

    logger.debug(f"\nThroughput: {ops_per_sec:.2f} ops/sec")

    assert ops_per_sec > 9000


@pytest.mark.asyncio
async def test_performance_method_injection(container):
    """
    Measures the overhead of _wrap_instance and method injection.
    """
    service = await container.resolve(UserService)

    start = time.perf_counter()
    ops = 10_000

    for _ in range(ops):
        # This triggers _resolve_kwargs logic every time
        await service.activate_user("user_123")

    duration = time.perf_counter() - start
    ops_per_sec = ops / duration

    logger.debug(f"\nMethod Injection Throughput: {ops_per_sec:.2f} ops/sec")

    # Reasonable target: > 2,000 ops/sec (Method injection is very slow)
    assert ops_per_sec > 1000


@pytest.mark.asyncio
async def test_performance_generic_resolution(container):
    """
    Measures the cost of resolving GenericAliases (Cache[int]) repeatedly.
    """
    start = time.perf_counter()
    ops = 5_000

    tasks = []
    for _ in range(ops):
        tasks.append(container.resolve(Cache[int]))

    await asyncio.gather(*tasks)

    duration = time.perf_counter() - start
    ops_per_sec = ops / duration

    logger.debug(f"\nGeneric Resolution Throughput: {ops_per_sec:.2f} ops/sec")

    assert ops_per_sec > 10000


@pytest.mark.asyncio
async def test_performance_sequential(container):
    start = time.perf_counter()
    ops = 5_000

    # Run one by one
    for _ in range(ops):
        await container.resolve(Cache[int])

    duration = time.perf_counter() - start
    ops_per_sec = ops / duration

    logger.debug(f"\nSequential Throughput: {ops_per_sec:.2f} ops/sec")

    assert ops_per_sec > 5000


@pytest.mark.asyncio
async def test_performance_deep_resolution(container):
    """
    Measures resolution of a nested dependency chain:
    UserService -> UserRepository -> (Database, Cache[str])

    This triggers 4 distinct resolution steps per call.
    """
    start = time.perf_counter()
    ops = 5_000

    for _ in range(ops):
        # This is the heavy lifter
        await container.resolve(UserService)

    duration = time.perf_counter() - start
    ops_per_sec = ops / duration

    logger.debug(f"\nDeep Graph Throughput: {ops_per_sec:.2f} ops/sec")

    assert ops_per_sec > 5000
