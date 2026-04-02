import asyncio
import contextlib

import pytest


@pytest.mark.asyncio
async def test_di_closes_generators_without_deadlocking(di):
    async def stubborn_provider():
        yield "resource"
        # If the DI container uses __anext__(), this sleep will execute and hang!
        # If it uses .aclose(), this sleep is instantly killed by GeneratorExit.
        await asyncio.sleep(999)

    di.add_scoped(t=str, generator=stubborn_provider)
    scope = di.scope()
    await scope.resolve(str)

    try:
        # We give the close() method 0.1 seconds to finish.
        await asyncio.wait_for(scope.close(), timeout=0.1)
    except asyncio.TimeoutError:
        pytest.fail("Memory Leak / Deadlock! The DI container used __anext__() "
                    "instead of aclose(), causing it to hang on the generator.")


@pytest.mark.asyncio
async def test_teardown_survives_cancelled_error(di):
    teardown_1_ran = False
    teardown_2_ran = False

    async def safe_dependency():
        nonlocal teardown_1_ran
        try:
            yield "safe"
        finally:
            teardown_1_ran = True

    async def volatile_dependency():
        nonlocal teardown_2_ran
        try:
            yield "volatile"
        finally:
            teardown_2_ran = True
            # Simulate a network library raising CancelledError during cleanup
            raise asyncio.CancelledError()

    di.add_scoped(t=int, generator=safe_dependency)
    di.add_scoped(t=float, generator=volatile_dependency)

    scope = di.scope()
    await scope.resolve(int)  # Resolves first, tears down LAST
    await scope.resolve(float)  # Resolves second, tears down FIRST

    with contextlib.suppress(asyncio.CancelledError):
        await scope.close()

    assert teardown_2_ran is True, "The volatile dependency should have started tearing down."
    assert teardown_1_ran is True, "The safe dependency was orphaned because the teardown loop broke!"
