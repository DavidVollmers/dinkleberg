from contextlib import asynccontextmanager

from fastapi import FastAPI

from dinkleberg import DependencyConfigurator
from dinkleberg.fastapi import di
from .example_service import ExampleService


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Set up Dinkleberg dependency configurator and store it in app state
    deps = app.state.dinkleberg = DependencyConfigurator()

    # Configure your dependencies
    deps.add_scoped(t=ExampleService)

    yield

    # Clean up resources
    await deps.close()


api = FastAPI(lifespan=lifespan)


# Use the di function to inject dependencies into your endpoints instead of FastAPI's Depends
@api.get("/example")
def example_endpoint(example_service=di(ExampleService)):
    return example_service.get_message()
