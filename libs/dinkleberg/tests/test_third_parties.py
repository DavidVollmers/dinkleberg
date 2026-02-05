import pytest
from pydantic import BaseModel


@pytest.mark.asyncio
async def test_pydantic_model(di):
    class TestModel(BaseModel):
        id: int
        name: str

        # Marking as non-dinkleberg to avoid instance wrapping
        __dinkleberg__ = False

    instance = TestModel(id=1, name='Test')

    di.add_singleton(t=TestModel, instance=instance)

    resolved_instance = await di.resolve(TestModel)

    assert resolved_instance is instance
