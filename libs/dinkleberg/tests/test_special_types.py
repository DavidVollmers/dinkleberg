from typing import NewType, Optional

import pytest


@pytest.mark.asyncio
async def test_new_type(di):
    class Session:
        pass

    # noinspection PyPep8Naming
    NewSessionType = NewType('NewSessionType', Session)

    session_instance = Session()
    di.add_singleton(t=NewSessionType, instance=NewSessionType(session_instance))

    resolved_instance = await di.resolve(NewSessionType)
    assert isinstance(resolved_instance, Session)
    assert resolved_instance is session_instance

    resolved_instance_direct = await di.resolve(Session)
    assert resolved_instance_direct is not session_instance


@pytest.mark.asyncio
async def test_optional(di):
    class Session:
        pass

    class App:
        def __init__(self, session: Optional[Session]):
            self.session = session

    instance = await di.resolve(App)
    assert isinstance(instance, App)
    assert instance.session is None

    singleton_instance = Session()
    di.add_singleton(t=Session, instance=singleton_instance)

    instance_with_session = await di.resolve(App)
    assert isinstance(instance_with_session, App)
    assert instance_with_session.session is singleton_instance
