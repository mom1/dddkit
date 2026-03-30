import asyncio
import time
from unittest.mock import Mock

import pytest

from dddkit.pydantic import EventBroker

from .conftest import BasketChanged, BasketChangedFactory

# Tests: Basic Handler Registration


def test_when_event_published_then_registered_handler_is_called(
    basket_changed_factory: type[BasketChangedFactory],
    event_broker_with_handler: tuple[EventBroker, Mock],
):
    """Handler subscribed to event type receives the published event."""
    event = basket_changed_factory.build()
    broker, handler = event_broker_with_handler

    broker(event)

    handler.assert_called_once()
    assert handler.call_args[0][0].basket_id == event.basket_id


async def test_when_event_published_async_then_async_handler_is_called(
    basket_changed_factory: type[BasketChangedFactory],
    event_broker_with_handler: tuple[EventBroker, Mock],
):
    """Async handler is awaited when event published in async context."""
    event = basket_changed_factory.build()
    broker, handler = event_broker_with_handler

    await broker(event)

    handler.assert_called_once()


# Tests: Mixed Handlers


async def test_given_mixed_handlers_when_published_async_then_both_called(
    basket_changed_factory: type[BasketChangedFactory],
    event_broker: EventBroker,
):
    """Both sync and async handlers are executed in async publish context."""
    event = basket_changed_factory.build()
    sync_handler = Mock()
    async_handler = Mock(return_value=asyncio.Future())
    async_handler.return_value.set_result(None)

    event_broker.subscribe(lambda e: isinstance(e, BasketChanged), sync_handler)  # pyright: ignore[reportUnknownArgumentType]
    event_broker.subscribe(lambda e: isinstance(e, BasketChanged), async_handler)  # pyright: ignore[reportUnknownArgumentType]

    await event_broker(event)

    sync_handler.assert_called_once()
    async_handler.assert_called_once()


# Tests: Parallel Execution


async def test_given_parallel_mode_when_multiple_async_handlers_then_run_concurrently(
    basket_changed_factory: type[BasketChangedFactory],
    parallel_event_broker: EventBroker,
):
    """Async handlers execute in parallel when parallel=True, reducing total time."""
    execution_order: list[str] = []
    start_time = time.monotonic()

    async def slow_handler_a(event: BasketChanged) -> None:
        await asyncio.sleep(0.05)
        execution_order.append('a')

    async def slow_handler_b(event: BasketChanged) -> None:
        await asyncio.sleep(0.05)
        execution_order.append('b')

    parallel_event_broker.subscribe(lambda e: isinstance(e, BasketChanged), slow_handler_a)  # pyright: ignore[reportUnknownArgumentType]
    parallel_event_broker.subscribe(lambda e: isinstance(e, BasketChanged), slow_handler_b)  # pyright: ignore[reportUnknownArgumentType]

    event = basket_changed_factory.build()

    await parallel_event_broker(event)
    elapsed = time.monotonic() - start_time

    assert len(execution_order) == 2
    assert set(execution_order) == {'a', 'b'}
    assert elapsed < 0.08, f'Expected parallel execution under 80ms, took {elapsed:.3f}s'


async def test_given_sequential_mode_when_multiple_async_handlers_then_both_executed(
    basket_changed_factory: type[BasketChangedFactory],
    event_broker: EventBroker,
):
    """Async handlers execute sequentially when parallel=False (default)."""
    handler_a = Mock()
    handler_b = Mock()

    @event_broker.instance(BasketChanged)
    async def _(event: BasketChanged) -> None:
        await asyncio.sleep(0.01)
        handler_a(event)

    @event_broker.instance(BasketChanged)
    async def _(event: BasketChanged) -> None:
        handler_b(event)

    event = basket_changed_factory.build()

    await event_broker(event)

    handler_a.assert_called_once()
    handler_b.assert_called_once()


async def test_given_parallel_mode_with_sync_handler_then_runs_in_thread_pool(
    basket_changed_factory: type[BasketChangedFactory],
    parallel_event_broker: EventBroker,
):
    """Sync handlers run in thread pool when parallel=True."""
    results: list[str] = []
    start_time = time.monotonic()

    def sync_handler(event: BasketChanged) -> None:
        time.sleep(0.05)
        results.append('sync')

    @parallel_event_broker.instance(BasketChanged)
    async def _(event: BasketChanged) -> None:
        await asyncio.sleep(0.05)
        results.append('async')

    parallel_event_broker.subscribe(lambda e: isinstance(e, BasketChanged), sync_handler)  # pyright: ignore[reportUnknownArgumentType]

    event = basket_changed_factory.build()

    await parallel_event_broker(event)
    elapsed = time.monotonic() - start_time

    assert elapsed < 0.15, f'Expected parallel execution under 150ms, took {elapsed:.3f}s'
    assert sorted(results) == ['async', 'sync']


# Tests: Handler Matching


def test_given_mixed_predicates_when_published_then_only_matching_handlers_called(
    basket_changed_factory: type[BasketChangedFactory],
    event_broker: EventBroker,
):
    """Only handlers with matching predicates receive the event."""
    event = basket_changed_factory.build()
    matching_handler = Mock()
    non_matching_handler = Mock()

    event_broker.subscribe(lambda e: isinstance(e, BasketChanged), matching_handler)  # pyright: ignore[reportUnknownArgumentType]
    event_broker.subscribe(lambda e: False, non_matching_handler)  # pyright: ignore[reportUnknownArgumentType]

    event_broker(event)

    matching_handler.assert_called_once()
    non_matching_handler.assert_not_called()


# Tests: Handler Uniqueness


async def test_given_multiple_matching_predicates_when_published_then_handler_called_once(
    basket_changed_factory: type[BasketChangedFactory],
    event_broker: EventBroker,
):
    """Handler matching multiple predicates receives event only once."""
    event = basket_changed_factory.build()
    handler = Mock()

    event_broker.subscribe(lambda e: isinstance(e, BasketChanged), handler)  # pyright: ignore[reportUnknownArgumentType]
    event_broker.subscribe(lambda e: hasattr(e, 'basket_id'), handler)  # pyright: ignore[reportUnknownArgumentType]

    await event_broker(event)

    handler.assert_called_once()


async def test_given_unsubscribed_handler_when_event_published_then_handler_not_called(
    basket_changed_factory: type[BasketChangedFactory],
    event_broker: EventBroker,
):
    """Unsubscribed handler does not receive events."""
    event = basket_changed_factory.build()
    unsubscribed_handler = Mock()
    active_handler = Mock()

    predicate = lambda e: isinstance(e, BasketChanged)  # pyright: ignore[reportUnknownVariableType,reportUnknownLambdaType]  # noqa: E731
    event_broker.subscribe(predicate, unsubscribed_handler)  # pyright: ignore[reportUnknownArgumentType]
    event_broker.subscribe(predicate, active_handler)  # pyright: ignore[reportUnknownArgumentType]
    event_broker.unsubscribe(predicate, unsubscribed_handler)  # pyright: ignore[reportUnknownArgumentType]

    await event_broker(event)

    unsubscribed_handler.assert_not_called()
    active_handler.assert_called_once()


def test_when_unsubscribe_from_nonexistent_predicate_then_no_error(
    event_broker: EventBroker,
):
    """Unsubscribing from predicate without subscribers is safe no-op."""
    handler = Mock()
    predicate = lambda e: isinstance(e, BasketChanged)  # pyright: ignore[reportUnknownVariableType,reportUnknownLambdaType]  # noqa: E731

    event_broker.unsubscribe(predicate, handler)  # pyright: ignore[reportUnknownArgumentType]


# Tests: Error Handling


def test_given_no_handlers_match_when_published_then_raises_not_implemented(
    basket_changed_factory: type[BasketChangedFactory],
    event_broker: EventBroker,
):
    """Publishing event with no matching handlers raises NotImplementedError."""
    event = basket_changed_factory.build()

    with pytest.raises(NotImplementedError, match='No suitable event handlers'):
        event_broker(event)


async def test_given_parallel_mode_no_handlers_when_published_then_raises_not_implemented(
    basket_changed_factory: type[BasketChangedFactory],
    parallel_event_broker: EventBroker,
):
    """Parallel mode raises NotImplementedError when no handlers match."""
    event = basket_changed_factory.build()

    with pytest.raises(NotImplementedError, match='No suitable event handlers'):
        await parallel_event_broker(event)


# Tests: Decorator Registration


def test_when_handler_registered_via_decorator_then_receives_events(
    basket_changed_factory: type[BasketChangedFactory],
    event_broker: EventBroker,
):
    """@broker.instance decorator registers handler correctly."""
    received_events: list[BasketChanged] = []

    @event_broker.instance(BasketChanged)
    def handler(event: BasketChanged) -> None:  # pyright: ignore[reportUnusedFunction]
        received_events.append(event)

    event = basket_changed_factory.build()

    event_broker(event)

    assert len(received_events) == 1
    assert received_events[0].basket_id == event.basket_id


def test_when_handler_registered_via_register_decorator_then_receives_events(
    basket_changed_factory: type[BasketChangedFactory],
    event_broker: EventBroker,
):
    """@broker.register decorator registers handler correctly."""
    received_events: list[BasketChanged] = []

    @event_broker.register(lambda e: isinstance(e, BasketChanged))  # pyright: ignore[reportUnknownArgumentType]
    def handler(event: BasketChanged) -> None:  # pyright: ignore[reportUnusedFunction]
        received_events.append(event)

    event = basket_changed_factory.build()

    event_broker(event)

    assert len(received_events) == 1
    assert received_events[0].basket_id == event.basket_id
