from typing import NewType

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
