import pytest
from typing import AsyncGenerator, Union, Optional

# Assuming your Dependency marker is imported like this
from dinkleberg.dependency import Dependency


# --- Dummy Classes for Testing ---

class Database:
    pass


class Cache:
    pass


class UserRepository:
    def __init__(self, db: Database):
        pass


class UserService:
    def __init__(self, repo: UserRepository):
        pass


class CircularA:
    def __init__(self, b: 'CircularB'):
        pass


class CircularB:
    def __init__(self, a: CircularA):
        pass


class Controller:
    def handle_request(self, db: Database = Dependency()):
        pass


# --- Tests ---

@pytest.mark.asyncio
async def test_inspector_direct_dependency(di):
    di.add_transient(t=Database)
    di.add_transient(t=UserRepository)

    assert di.inspector.has_dependency(UserRepository, Database) is True
    assert di.inspector.has_dependency(UserRepository, Cache) is False


@pytest.mark.asyncio
async def test_inspector_transitive_dependency(di):
    di.add_transient(t=Database)
    di.add_transient(t=UserRepository)
    di.add_transient(t=UserService)

    # UserService -> UserRepository -> Database
    assert di.inspector.has_dependency(UserService, Database) is True


@pytest.mark.asyncio
async def test_inspector_circular_dependency_safety(di):
    di.add_transient(t=CircularA)
    di.add_transient(t=CircularB)

    # Should safely return False for a non-existent dependency
    # without hitting a RecursionError
    assert di.inspector.has_dependency(CircularA, Database) is False

    # It should correctly identify the circular link
    assert di.inspector.has_dependency(CircularA, CircularB) is True
    assert di.inspector.has_dependency(CircularB, CircularA) is True


@pytest.mark.asyncio
async def test_inspector_callable_factory_dependency(di):
    def user_service_factory(db: Database) -> UserService:
        return UserService(UserRepository(db))

    di.add_transient(t=Database)
    di.add_transient(t=UserService, callable=user_service_factory)

    # The factory requires Database, so looking up UserService should reveal it
    assert di.inspector.has_dependency(UserService, Database) is True


@pytest.mark.asyncio
async def test_inspector_generator_factory_dependency(di):
    async def db_generator(cache: Cache) -> AsyncGenerator[Database, None]:
        yield Database()

    di.add_transient(t=Cache)
    di.add_scoped(t=Database, generator=db_generator)

    # The generator requires Cache
    assert di.inspector.has_dependency(Database, Cache) is True


@pytest.mark.asyncio
async def test_inspector_method_injection_dependency(di):
    di.add_transient(t=Database)
    di.add_transient(t=Controller)

    # Controller has a method with `db: Database = Dependency()`
    assert di.inspector.has_dependency(Controller, Database) is True


@pytest.mark.asyncio
async def test_inspector_unregistered_type_fallback(di):
    # Even if types aren't registered, the inspector should fallback
    # to inspecting the target class directly
    assert di.inspector.has_dependency(UserService, Database) is True


@pytest.mark.asyncio
async def test_inspector_specific_method(di):
    di.add_transient(t=Database)

    class WebController:
        def handle(self, db: Database = Dependency()):
            pass

        def process(self):  # No dependencies
            pass

    # Inspecting the class finds the dependency (via scanning all methods)
    assert di.inspector.has_dependency(WebController, Database) is True

    # Inspecting the specific method finds it
    assert di.inspector.has_dependency(WebController.handle, Database) is True

    # Inspecting the unrelated method returns False
    assert di.inspector.has_dependency(WebController.process, Database) is False


HeaderTypes = Union[str, dict]


class ConfigTypes:
    pass


class FailingService:
    # Simulates the bug where Union types crashed the static param inspector
    def __init__(self, headers: HeaderTypes | None, config: Optional[ConfigTypes]):
        pass


class ForwardService:
    # Simulates string forward references
    def __init__(self, db: 'Database'):
        pass


@pytest.mark.asyncio
async def test_inspector_ignores_non_callable_types(di):
    # This should safely evaluate to False without raising a TypeError
    # from the `HeaderTypes | None` union.
    assert di.inspector.has_dependency(FailingService, Database) is False

    # It should still correctly extract the inner type of an Optional
    assert di.inspector.has_dependency(FailingService, ConfigTypes) is True


@pytest.mark.asyncio
async def test_inspector_string_forward_references(di):
    di.add_transient(t=Database)
    di.add_transient(t=ForwardService)

    # The inspector should resolve the string 'Database'
    # to the registered Database type
    assert di.inspector.has_dependency(ForwardService, Database) is True


@pytest.mark.asyncio
async def test_inspector_unregistered_string_forward_references(di):
    # If the string reference isn't registered yet, it shouldn't crash,
    # but it also won't know that 'Database' == Database class.
    assert di.inspector.has_dependency(ForwardService, Database) is False
