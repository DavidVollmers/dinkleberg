from typing import AsyncGenerator

import pytest


@pytest.mark.asyncio
async def test_generator_lifecycle(di):
    events = []

    class Database:
        pass

    async def db_generator() -> AsyncGenerator[Database, None]:
        events.append('setup')
        yield Database()
        events.append('teardown')

    di.add_scoped(t=Database, generator=db_generator)

    db = await di.resolve(Database)
    assert isinstance(db, Database)
    assert events == ['setup']

    await di.close()
    assert events == ['setup', 'teardown']


@pytest.mark.asyncio
async def test_generator_no_yield_failure(di):
    class Empty:
        pass

    async def empty_gen() -> AsyncGenerator[Empty, None]:
        if False:
            yield Empty()

    di.add_scoped(t=Empty, generator=empty_gen)

    with pytest.raises(RuntimeError, match='did not yield any value'):
        await di.resolve(Empty)


@pytest.mark.asyncio
async def test_generator_teardown_failure(di):
    class BadCleanup:
        pass

    async def bad_cleanup_gen() -> AsyncGenerator[BadCleanup, None]:
        yield BadCleanup()
        raise ValueError('Boom teardown')

    di.add_scoped(t=BadCleanup, generator=bad_cleanup_gen)
    await di.resolve(BadCleanup)

    with pytest.raises(ExceptionGroup, match='Errors occurred during closing DependencyConfigurator') as group:
        await di.close()

    exceptions = group.value.exceptions
    assert len(exceptions) == 1
    assert isinstance(exceptions[0], ValueError)
    assert str(exceptions[0]) == 'Boom teardown'


@pytest.mark.asyncio
async def test_scope_independent_disposal(di):
    events = []

    class Resource:
        def __init__(self, name):
            self.name = name

    def create_gen(name):
        async def gen():
            events.append(f'{name}_start')
            yield Resource(name)
            events.append(f'{name}_stop')

        return gen

    # Register in parent, creating scope copies the registration
    di.add_scoped(t=Resource, generator=create_gen('res'))

    # Resolve in Parent
    await di.resolve(Resource)

    # Resolve in Scope
    scope = di.scope()
    # To differentiate, we overwrite registration in scope or just rely on new instance logic.
    # Since your code creates new instances per scope, running resolve again creates a new generator.
    await scope.resolve(Resource)

    assert events == ['res_start', 'res_start']

    # Dispose Scope only
    await scope.close()
    assert events == ['res_start', 'res_start', 'res_stop']

    # Dispose Parent
    await di.close()
    assert events == ['res_start', 'res_start', 'res_stop', 'res_stop']


@pytest.mark.asyncio
async def test_generator_lifo_disposal(di):
    events = []

    class LowLevel:
        pass

    class HighLevel:
        def __init__(self, child: LowLevel):
            self.child = child

    async def low_gen() -> AsyncGenerator[LowLevel, None]:
        events.append('low_start')
        yield LowLevel()
        events.append('low_stop')

    async def high_gen(child: LowLevel) -> AsyncGenerator[HighLevel, None]:
        events.append('high_start')
        yield HighLevel(child)
        events.append('high_stop')

    di.add_scoped(t=LowLevel, generator=low_gen)
    di.add_scoped(t=HighLevel, generator=high_gen)

    await di.resolve(HighLevel)

    # Setup order: Low -> High
    assert events == ['low_start', 'high_start']

    await di.close()

    # Teardown order: High -> Low (LIFO)
    assert events == ['low_start', 'high_start', 'high_stop', 'low_stop']
