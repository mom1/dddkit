from typing import cast
from uuid import uuid4

import pytest

from dddkit.dataclasses import DomainEvent, EventBroker

from .conftest import BasketChanged, BasketId


def test_handle_event(handle_event: EventBroker):
    basket_id = cast(BasketId, uuid4())
    call_count: int = 0

    @handle_event.instance(BasketChanged)
    def _(event: BasketChanged) -> None:
        nonlocal call_count

        call_count += 1
        assert event.basket_id == basket_id

    handle_event(BasketChanged(basket_id=basket_id))
    assert call_count == 1


async def test_async_publish(handle_event: EventBroker):
    basket_id = cast(BasketId, uuid4())
    call_count: int = 0

    @handle_event.instance(BasketChanged)
    async def _(event: BasketChanged):
        nonlocal call_count

        call_count += 1
        assert event.basket_id == basket_id

    await handle_event(BasketChanged(basket_id=basket_id))
    assert call_count == 1


async def test_async_publish_sync_handle(handle_event: EventBroker):
    basket_id = cast(BasketId, uuid4())
    call_count: int = 0

    @handle_event.instance(BasketChanged)
    def _(event: BasketChanged):
        nonlocal call_count

        call_count += 1
        assert event.basket_id == basket_id

    await handle_event(BasketChanged(basket_id=basket_id))
    assert call_count == 1


async def test_only_once_receive(handle_event: EventBroker):
    basket_id = cast(BasketId, uuid4())
    call_count: int = 0

    @handle_event.register(lambda event: False)
    def _(_: DomainEvent):
        nonlocal call_count

        call_count += 1

    @handle_event.register(lambda event: isinstance(event, BasketChanged))
    @handle_event.instance(BasketChanged)
    def _(event: BasketChanged):
        nonlocal call_count

        call_count += 1
        assert event.basket_id == basket_id

    await handle_event(BasketChanged(basket_id=basket_id))

    assert call_count == 1


def test_unsubscribe(handle_event: EventBroker):
    basket_id = cast(BasketId, uuid4())
    call_count: int = 0

    def predicate(event: DomainEvent):
        return isinstance(event, BasketChanged)

    def fake_handle(event: BasketChanged):
        assert event.basket_id == basket_id

    def _handle(event: BasketChanged):
        nonlocal call_count

        call_count += 1
        assert event.basket_id == basket_id

    handle_event.unsubscribe(predicate, fake_handle)
    handle_event.register(predicate)(_handle)
    handle_event.register(predicate)(fake_handle)
    handle_event.unsubscribe(predicate, _handle)
    handle_event.unsubscribe(predicate, _handle)
    handle_event(BasketChanged(basket_id=basket_id))

    assert call_count == 0


def test_unhandled_event(handle_event: EventBroker):
    basket_id = cast(BasketId, uuid4())
    event = BasketChanged(basket_id=basket_id)
    with pytest.raises(NotImplementedError, match='No suitable event handlers found'):
        handle_event(event)
