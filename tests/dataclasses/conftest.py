from dataclasses import dataclass
from typing import NewType, cast
from uuid import UUID, uuid4

import pytest

from dddkit.dataclasses import Aggregate, AggregateEvent, DomainEvent, EventBroker

BasketId = NewType('BasketId', UUID)


@dataclass(frozen=True, kw_only=True)
class BasketChanged(DomainEvent):
    basket_id: BasketId


@dataclass(kw_only=True)
class Basket(Aggregate):
    basket_id: BasketId

    class Created(AggregateEvent):
        """Event for basket creation."""

    class Changed(AggregateEvent):
        """Event for basket changed."""

    class ChangedId(Changed):
        basket_id: BasketId

    class Deleted(AggregateEvent):
        """Event for basket deletion."""

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
def basket() -> Basket:
    return Basket(basket_id=cast(BasketId, uuid4()))


@pytest.fixture(name='handle_event')
def handle_event_factory() -> EventBroker:
    return EventBroker()
