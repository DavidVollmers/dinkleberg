import pytest
from pydantic import BaseModel, field_validator


@pytest.mark.asyncio
async def test_pydantic_model(di):
    class TestModel(BaseModel):
        id: int
        name: str

    instance = TestModel(id=1, name='Test')

    di.add_singleton(t=TestModel, instance=instance)

    resolved_instance = await di.resolve(TestModel)

    assert resolved_instance is instance


@pytest.mark.asyncio
async def test_pydantic_model_with_validator(di):
    # noinspection PyMethodParameters
    class TestModel(BaseModel):
        id: int
        name: str

        @field_validator('name')
        def validate_name(cls, value):
            if not value:
                raise ValueError('Name cannot be empty')
            return value

    instance = TestModel(id=1, name='Test')

    di.add_singleton(t=TestModel, instance=instance)

    resolved_instance = await di.resolve(TestModel)

    assert resolved_instance is instance
