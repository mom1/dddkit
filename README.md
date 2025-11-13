# DDDKit

<div align="center">
    <picture>
      <img src="https://raw.githubusercontent.com/mom1/dddkit/main/static/kid_ddd.png"
        alt="DDDKit" style="width: 50%; height: auto;" />
    </picture>
</div>

[![PyPI](https://img.shields.io/pypi/v/dddkit.svg)](https://pypi.org/project/dddkit/)
[![Python Version](https://img.shields.io/pypi/pyversions/dddkit.svg)](https://pypi.org/project/dddkit/)
![PyPI - Downloads](https://img.shields.io/pypi/dm/dddkit.svg?label=pip%20installs&logo=python)

[![Gitmoji](https://img.shields.io/badge/gitmoji-%20😜%20😍-FFDD67.svg)](https://gitmoji.dev)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://docs.astral.sh/ruff/)
[![UV](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://docs.astral.sh/uv/)

![GitHub issues](https://img.shields.io/github/issues/mom1/dddkit.svg)
![GitHub stars](https://img.shields.io/github/stars/mom1/dddkit.svg)
![GitHub Release Date](https://img.shields.io/github/release-date/mom1/dddkit.svg)
![GitHub commits since latest release](https://img.shields.io/github/commits-since/mom1/dddkit/latest.svg)
![GitHub last commit](https://img.shields.io/github/last-commit/mom1/dddkit.svg)
[![GitHub license](https://img.shields.io/github/license/mom1/dddkit)](https://github.com/mom1/dddkit/blob/master/LICENSE)

Kit for using DDD (Domain-Driven Design) tactical patterns in Python.

## Overview

`dddkit` is a Python library designed to facilitate the implementation of Domain-Driven Design tactical patterns. It
provides base classes and utilities for common DDD concepts such as Aggregates, Entities, Value Objects, Domain Events,
and Repositories.

The library offers both `dataclasses` and `pydantic` implementations of DDD patterns to accommodate different project
needs and preferences.

## Features

- **Aggregate**: Base class for DDD aggregates with event handling capabilities
- **Entity**: Base class for entities with identity
- **ValueObject**: Base class for value objects without identity
- **Domain Events**: Support for domain event creation and handling
- **Event Brokers**: Synchronous and asynchronous event brokers for event processing
- **Repositories**: Base repository pattern implementation
- **Changes Handler**: Mechanism to handle aggregate changes and events
- **Stories**: A pattern for defining and executing sequential business operations with hooks and execution tracking

## Installation

### Prerequisites

This project uses [uv](https://docs.astral.sh/uv/) for Python and dependency management. Install it first:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Or with [brew](https://brew.sh/) on macOS:

```bash
brew install uv
```

### Installing dddkit

Install with uv from PyPI:

```bash
uv pip install dddkit
```

Or with pip:

```bash
pip install dddkit
```

### For Development

To set up the development environment:

```bash
# Clone the repository
git clone https://github.com/mom1/dddkit.git

# Navigate to the project directory
cd dddkit

# Install dependencies
make install
```

## Usage

### Basic Usage

The library provides two implementations of DDD patterns:

1. **dataclasses**: Using Python's built-in `dataclasses`
2. **pydantic**: Using the `pydantic` library (optional dependency)

#### Using dataclasses implementation

```python
from typing import NewType
from dataclasses import dataclass, field
from dddkit.dataclasses import Aggregate, Entity

ProductName = NewType('ProductName', str)
ProductId = NewType('ProductId', int)
BasketId = NewType('BasketId', int)


@dataclass(kw_only=True)
class Product(Entity):
  product_id: ProductId
  name: ProductName
  amount: float = 0


@dataclass(kw_only=True)
class Basket(Aggregate):
  basket_id: BasketId
  items: dict[ProductId, Product] = field(default_factory=dict)

  @classmethod
  def new(cls, basket_id: BasketId):
    return cls(basket_id=basket_id)

  def add_item(self, item: Product):
    if _item := self.items.get(item.product_id):
      _item.amount = item.amount


# Use repositories and event handling
from dddkit.dataclasses import Repository


class BasketRepository(Repository[Basket, BasketId]):
  """Repository for basket"""
```

#### Using pydantic implementation

First install the optional pydantic dependency:

```bash
uv pip install dddkit[pydantic]
```

```python
from typing import NewType
from dddkit.pydantic import Aggregate, Entity, AggregateEvent
from pydantic import Field

ProductName = NewType('ProductName', str)
ProductId = NewType('ProductId', int)
BasketId = NewType('BasketId', int)


class Product(Entity):
  product_id: ProductId
  name: ProductName
  amount: float = 0


class Basket(Aggregate):
  basket_id: BasketId
  items: dict[ProductId, Product] = Field(default_factory=dict)

  @classmethod
  def new(cls, basket_id: BasketId):
    return cls(basket_id=basket_id)

  def add_item(self, item: Product):
    if _item := self.items.get(item.product_id):
      _item.amount = item.amount


# Use repositories and event handling
from dddkit.pydantic import Repository


class BasketRepository(Repository[Basket, BasketId]):
  """Repository for basket"""
```

### Aggregate Events

```python
from typing import NewType
from dataclasses import dataclass, field
from dddkit.dataclasses import Aggregate, Entity, AggregateEvent

ProductName = NewType('ProductName', str)
ProductId = NewType('ProductId', int)
BasketId = NewType('BasketId', int)


@dataclass(kw_only=True)
class Product(Entity):
  product_id: ProductId
  name: ProductName
  amount: float = 0


@dataclass(kw_only=True)
class Basket(Aggregate):
  basket_id: BasketId
  items: dict[ProductId, Product] = field(default_factory=dict)

  @dataclass(frozen=True, kw_only=True)
  class Created(AggregateEvent):
    """Basket created event"""

  @dataclass(frozen=True, kw_only=True)
  class AddedItem(AggregateEvent):
    item: Product

  @classmethod
  def new(cls, basket_id: BasketId):
    basket = cls(basket_id=basket_id)
    basket.add_event(cls.Created())
    return basket

  def add_item(self, item: Product):
    if _item := self.items.get(item.product_id):
      _item.amount = item.amount
      self.add_event(self.AddedItem(item=_item))
```

### Event Handling

```python
from dddkit.dataclasses import EventBroker

handle_event = EventBroker()


# sync

@handle_event.handle(ProductCreated)
def _(event: ProductCreated):
  # Handle the event
  print(f"Product {event.name} created with ID {event.product_id}")


product_event = ProductCreated(product_id=ProductId("123"), name="Test Product")


def context():
  handle_event(product_event)


# Or async

@handle_event.handle(ProductCreated)
async def _(event: ProductCreated):
  # Handle the event
  print(f"Product {event.name} created with ID {event.product_id}")


async def context():
  await handle_event(product_event)
```

### Stories

Stories provide a pattern for defining sequential business operations with optional hooks for execution tracking,
logging, and timing.

> **Note**: The stories implementation in DDDKit was inspired by and uses parts of the work from [proofit404/stories](https://github.com/proofit404/stories).

#### Basic Story Usage

```python
from dataclasses import dataclass
from dddkit.stories import I, Story
from types import SimpleNamespace


@dataclass(frozen=True, slots=True)
class ShoppingCartStory(Story):
  # Define the steps in the story
  I.add_item
  I.apply_discount
  I.calculate_total

  class State(SimpleNamespace):
    items: list = []
    discount: float = 0.0
    total: float = 0.0

  def add_item(self, state: State):
    state.items.append({"name": "Product A", "price": 10.0})

  def apply_discount(self, state: State):
    if len(state.items) > 1:
      state.discount = 0.1  # 10% discount

  def calculate_total(self, state: State):
    subtotal = sum(item["price"] for item in state.items)
    state.total = subtotal * (1 - state.discount)


# Execute the story
story = ShoppingCartStory()
state = story.State()
story(state)

print(f"Items: {state.items}")
print(f"Discount: {state.discount}")
print(f"Total: {state.total}")
```

#### Stories with Async Operations

Stories support both synchronous and asynchronous operations:

```python
import asyncio
from dataclasses import dataclass
from dddkit.stories import I, Story
from types import SimpleNamespace


@dataclass(frozen=True, slots=True)
class AsyncProcessingStory(Story):
  I.fetch_data
  I.process_data
  I.save_result

  class State(SimpleNamespace):
    raw_data: str = ""
    processed_data: str = ""
    saved: bool = False

  async def fetch_data(self, state: State):
    # Simulate async data fetching
    await asyncio.sleep(0.1)
    state.raw_data = "some raw data"

  def process_data(self, state: State):
    state.processed_data = state.raw_data.upper()

  async def save_result(self, state: State):
    # Simulate async saving
    await asyncio.sleep(0.05)
    state.saved = True


# Execute the async story
async def run_async_story():
  story = AsyncProcessingStory()
  state = story.State()
  await story(state)
  return state

# asyncio.run(run_async_story())
```

#### Stories with Hooks

Stories support hooks for execution tracking, logging, and performance monitoring:

```python
from dataclasses import dataclass
from dddkit.stories import I, Story, inject_hooks, ExecutionTimeTracker, StatusTracker, LoggingHook
from types import SimpleNamespace


@dataclass(frozen=True, slots=True)
class HookedStory(Story):
  I.step_one
  I.step_two
  I.step_three

  class State(SimpleNamespace):
    step_one_completed: bool = False
    step_two_completed: bool = False
    step_three_completed: bool = False

  def step_one(self, state: State):
    state.step_one_completed = True

  def step_two(self, state: State):
    state.step_two_completed = True

  def step_three(self, state: State):
    state.step_three_completed = True


# Inject default hooks (StatusTracker, ExecutionTimeTracker, LoggingHook)
story_class = HookedStory
inject_hooks(story_class)

# Execute the story with hooks
story = story_class()
state = story.State()
story(state)
```

```shell
# At the DEBUG log level, you will see the process of executing story steps.
HookedStory:
    ⟳I.step_one
    I.step_two
    I.step_three
HookedStory:
    ✓I.step_one [0.000s]
    ⟳I.step_two
    I.step_three
HookedStory:
    ✓I.step_one [0.000s]
    ✓I.step_two [0.001s]
    ⟳I.step_three
# If an error occurs during the execution of a story, it will look like this
HookedStory:
    ✓I.step_one [0.000s]
    ✓I.step_two [0.001s]
    ✗I.step_three
Traceback (most recent call last):
  File "/your_file.py", line 115, in your_function
  ...
exceptions.YourException
```

Stories provide three types of hooks:

- `before`: Runs before each step
- `after`: Runs after each step (even if exceptions occur)
- `error`: Runs when an exception occurs in a step

You can also create custom hooks:

```python
from dddkit.stories import StoryExecutionContext, StepExecutionInfo, inject_hooks


class CustomHook:
  def before(self, context: StoryExecutionContext, step_info: StepExecutionInfo):
    print(f"Starting step: {step_info.step_name}")

  def after(self, context: StoryExecutionContext, step_info: StepExecutionInfo):
    print(f"Completed step: {step_info.step_name}")

  def error(self, context: StoryExecutionContext, step_info: StepExecutionInfo):
    print(f"Error in step: {step_info.step_name}, Error: {step_info.error}")


# Inject custom hooks
inject_hooks(HookedStory, hooks=[CustomHook()])
```

## Project Structure

```shell
src/dddkit/
├── __init__.py
├── dataclasses/        # DDD patterns using dataclasses
│   ├── __init__.py
│   ├── aggregates.py
│   ├── changes_handler.py
│   ├── events.py
│   └── repositories.py
├── pydantic/          # DDD patterns using pydantic
│   ├── __init__.py
│   ├── aggregates.py
│   ├── changes_handler.py
│   ├── events.py
│   └── repositories.py
└── stories/           # Stories pattern for sequential operations
    ├── __init__.py
    ├── story.py       # Core Story implementation
    └── hooks.py       # Hook implementations for stories
```

## Contributing

Contributions are welcome! Here's how you can get started:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests if applicable
5. Run the test suite (`make test`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Development Commands

```shell
make install    # Install dependencies
make test       # Run tests
make lint       # Run linter
make format     # Run formatter
make build      # Build the package
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Development Status

This project is in production/stable state. All contributions and feedback are welcome.
