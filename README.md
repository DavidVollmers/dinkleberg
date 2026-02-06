# dinkleberg

> "And this is where I'd put my working dependencies... IF I HAD ANY!"

**dinkleberg** is a lightweight Python utility designed to make dependency management less of a neighborhood feud. Built
to work seamlessly in any project, it ensures your environment stays green—unlike the guy's next door.

## Installation

```bash
pip install dinkleberg

uv add dinkleberg
```

## Why dinkleberg?

- 🚀 Async Native: Built from the ground up for asyncio.

- 🧬 Generics Support: First-class support for Generic[T]. Resolve Repository[User] and it just works.

- ⚡ High Performance: heavily optimized reflection caching and optimistic resolution (10k+ ops/sec).

- 💉 Method Injection: Inject dependencies directly into method signatures using Dependency().

- 🧹 Clean API: No global state, no decorators required on your classes.

## Quick Start

Register your classes and let `dinkleberg` figure out the rest.

```python
import asyncio
from dinkleberg import DependencyConfigurator


class Database:
    def __init__(self):
        self.connected = True


class UserService:
    # Automatic Constructor Injection
    def __init__(self, db: Database):
        self.db = db


async def main():
    di = DependencyConfigurator()

    # 1. Register
    di.add_singleton(t=Database)
    di.add_transient(t=UserService)

    # 2. Resolve
    service = await di.resolve(UserService)

    print(f"Service connected: {service.db.connected}")


if __name__ == "__main__":
    asyncio.run(main())
```

### Generics 🧬

Most Python DI containers struggle with Generics. `dinkleberg` thrives on them. You don't need to register every
variation manually.

```python
class Repository[T]:
    def __init__(self, model_type: type[T]):
        self.model_type = model_type


class User: pass


class Product: pass


async def main():
    di = DependencyConfigurator()

    # Register the generic definition ONCE
    di.add_transient(t=Repository)

    # Resolve variations on the fly!
    user_repo = await di.resolve(Repository[User])
    product_repo = await di.resolve(Repository[Product])

    assert user_repo.model_type is User
    assert product_repo.model_type is Product
```

### Method Injection 💉

Sometimes you don't want to pollute your `__init__`. You can inject dependencies directly into method calls using
default values.

```python
from dinkleberg import Dependency


class EmailService:
    def send(self, msg):
        print(f"Sending: {msg}")


async def main():
    di = DependencyConfigurator()
    di.add_singleton(t=EmailService)

    # Mark parameters with Dependency()
    async def welcome_user(name: str, emailer: EmailService = Dependency()):
        emailer.send(f"Welcome, {name}!")

    # Resolve the function itself (dinkleberg wraps it)
    func = await di.resolve(welcome_user)

    # Call it without the dependency - it's auto-injected!
    await func("Timmy")
```

#### Overriding Dependencies

You aren't locked in. You can override dependencies at call time by passing arguments manually or configuring the
`Dependency`.

```python
# Override at call time
await func("Timmy", emailer=MockEmailService())


# Pass kwargs to the resolved dependency
async def test(service: MyService = Dependency(config="debug_mode")):
    ...
```

---

## Lifetimes

| Lifetime  | Method          | Description                                                          |
| --------- | --------------- | -------------------------------------------------------------------- |
| Transient | `add_transient` | A new instance is created every time it is requested.                |
| Singleton | `add_singleton` | The same instance is reused for the entire application lifetime.     |
| Scoped    | `add_scoped`    | A new instance is created once per scope() (e.g., per HTTP request). |

### Using Scopes

```python
root_di = DependencyConfigurator()
root_di.add_scoped(t=Session)

# Create a new scope (e.g., for an incoming request)
request_scope = root_di.scope()

# This instance lives as long as 'request_scope' is alive
session = await request_scope.resolve(Session)

# Cleanup (runs async generators/cleanup logic)
await request_scope.close()
```

---

## Performance

`dinkleberg` is optimized for high-throughput applications.

- **Smart Caching**: `inspect.signature` and type hints are cached globally to avoid runtime parsing overhead.

- **Optimistic Resolution**: If a dependency is a known singleton, it is resolved synchronously without touching the
  asyncio event loop.

- **Lazy Wrapping**: Only methods that actually use `Dependency()` are inspected/wrapped.

## License

MIT License. Because sharing is caring, unlike Dinkleberg...
