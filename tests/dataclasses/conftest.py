from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, NewType, cast, final
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from polyfactory.factories import DataclassFactory
from typing_extensions import override

from dddkit.dataclasses import Aggregate, AggregateEvent, DomainEvent, EventBroker

BasketId = NewType('BasketId', UUID)


@dataclass(frozen=True, kw_only=True)
class BasketChanged(DomainEvent):
    basket_id: BasketId


@dataclass(kw_only=True)
class Basket(Aggregate):
    basket_id: BasketId

    @dataclass(frozen=True, kw_only=True)
    class Created(AggregateEvent): ...

    @dataclass(frozen=True, kw_only=True)
    class Changed(AggregateEvent): ...

    @dataclass(frozen=True, kw_only=True)
    class ChangedId(Changed):
        basket_id: BasketId

    @dataclass(frozen=True, kw_only=True)
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
    return EventBroker(parallel=False)


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
class BasketFactory(DataclassFactory[Basket]):
    """Factory for Basket aggregates."""

    __model__: type[Basket] = Basket
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
class BasketChangedFactory(DataclassFactory[BasketChanged]):
    """Factory for BasketChanged events."""

    __model__: type[BasketChanged] = BasketChanged
    __random_seed__ = 42


@pytest.fixture
def basket_changed_factory() -> type[BasketChangedFactory]:
    return BasketChangedFactory
