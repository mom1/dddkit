from collections.abc import Callable
from typing import Any, NewType, cast, final
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from polyfactory.factories.pydantic_factory import ModelFactory
from typing_extensions import override

from dddkit.pydantic import Aggregate, AggregateEvent, DomainEvent, EventBroker

BasketId = NewType('BasketId', UUID)


class BasketChanged(DomainEvent):
    basket_id: BasketId


class Basket(Aggregate):
    basket_id: BasketId

    class Created(AggregateEvent): ...

    class Changed(AggregateEvent): ...

    class ChangedId(Changed):
        basket_id: BasketId

    class Deleted(AggregateEvent): ...

    @classmethod
    def new(cls, basket_id: BasketId) -> 'Basket':
        basket = cls(basket_id=basket_id)
        basket.add_event(cls.Created())
        return basket

    def change_id(self, basket_id: BasketId) -> None:
        self.basket_id = basket_id
        self.add_event(self.ChangedId(basket_id=basket_id))

    def delete(self) -> None:
        self.add_event(self.Deleted())


@pytest.fixture
def event_broker() -> EventBroker:
    return EventBroker()


@pytest.fixture
def parallel_event_broker() -> EventBroker:
    return EventBroker(parallel=True)


@pytest.fixture
def event_broker_with_handler() -> tuple[EventBroker, Mock]:
    broker = EventBroker()
    handler = Mock()
    broker.subscribe(lambda event: isinstance(event, BasketChanged), handler)
    return broker, handler


@final
class BasketFactory(ModelFactory[Basket]):
    """Factory for Basket aggregates."""

    __model__ = Basket
    __random_seed__ = 42

    @classmethod
    @override
    def get_provider_map(cls) -> dict[type, Callable[[], Any]]:
        providers = super().get_provider_map()
        providers[BasketId] = lambda: cast(BasketId, uuid4())
        return providers

    @classmethod
    def created(cls, basket_id: BasketId | None = None) -> Basket:
        return Basket.new(basket_id=basket_id or cast(BasketId, uuid4()))


@pytest.fixture
def basket_factory() -> type[BasketFactory]:
    return BasketFactory


@final
class BasketChangedFactory(ModelFactory[BasketChanged]):
    """Factory for BasketChanged events."""

    __model__ = BasketChanged
    __random_seed__ = 42


@pytest.fixture
def basket_changed_factory() -> type[BasketChangedFactory]:
    return BasketChangedFactory
