import asyncio
import pytest
from dinkleberg import DependencyConfigurator


@pytest.mark.asyncio
async def test_singleton_race_condition(di: DependencyConfigurator):
    instances = []

    # We need a dependency to force _resolve_factory_kwargs
    # to hit the 'await asyncio.gather' path and yield control.
    class SomeDependency:
        pass

    class RaceConditionSingleton:
        def __init__(self, dep: SomeDependency):
            instances.append(self)

    di.add_transient(t=SomeDependency)
    di.add_singleton(t=RaceConditionSingleton)

    # Create 50 concurrent requests for the singleton
    tasks = [di.resolve(RaceConditionSingleton) for _ in range(50)]

    # Execute them all simultaneously on the event loop
    results = await asyncio.gather(*tasks)

    assert len(instances) == 1, f'Expected exactly 1 singleton instance, but got {len(instances)}'

    # Double-check that every concurrent task received the exact same memory address
    first_instance = results[0]
    for res in results[1:]:
        assert res is first_instance
