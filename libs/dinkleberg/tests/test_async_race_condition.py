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


@pytest.mark.asyncio
async def test_scoped_race_condition(di: DependencyConfigurator):
    instances = []

    # The catalyst dependency that forces the event loop to yield
    class SlowDependency:
        pass

    class ScopedResource:
        def __init__(self, dep: SlowDependency):
            instances.append(self)

    di.add_transient(t=SlowDependency)
    di.add_scoped(t=ScopedResource)

    # --- SIMULATE REQUEST 1 ---
    scope1 = di.scope()

    # 50 concurrent resolutions inside the FIRST scope
    tasks_scope1 = [scope1.resolve(ScopedResource) for _ in range(50)]
    results_scope1 = await asyncio.gather(*tasks_scope1)

    # Without the lock, this will fail. With the lock, it passes.
    assert len(instances) == 1, f'Expected exactly 1 instance for scope1, but got {len(instances)}'

    # Verify all 50 tasks in scope1 share the exact same memory address
    first_instance_s1 = results_scope1[0]
    for res in results_scope1[1:]:
        assert res is first_instance_s1

    # --- SIMULATE REQUEST 2 ---
    scope2 = di.scope()

    # 50 concurrent resolutions inside the SECOND scope
    tasks_scope2 = [scope2.resolve(ScopedResource) for _ in range(50)]
    results_scope2 = await asyncio.gather(*tasks_scope2)

    # Now there should be exactly 2 instances in total (one per scope)
    assert len(instances) == 2, f'Expected 2 total instances across both scopes, but got {len(instances)}'

    # Verify all 50 tasks in scope2 share their own identical memory address
    first_instance_s2 = results_scope2[0]
    for res in results_scope2[1:]:
        assert res is first_instance_s2

    # CRITICAL: Prove that the scopes did not accidentally share the same instance!
    assert first_instance_s1 is not first_instance_s2, 'Scope 1 and Scope 2 incorrectly shared the same instance!'
