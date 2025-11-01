"""Module for basic aggregate classes.

Example:
-------
    from dddkit.dataclasses import Aggregate

    BasketId = NewType('BasketId', UUID)

    @dataclass(kw_only=True)
    class Basket(Aggregate):
        basket_id: BasketId

        class Created(AggregateEvent):
            '''Event for basket creation.'''

        class Changed(AggregateEvent):
            '''Event for basket change.'''

        class ChangedId(Changed):
            basket_id: BasketId

        class Deleted(AggregateEvent):
            '''Event for basket deletion.'''


        @classmethod
        def new(cls, basket_id: BasketId) -> Basket:
            basket = cls(basket_id=basket_id)
            basket.add_event(cls.Created())
            return basket

        def change_id(self, basket_id: BasketId) -> None:
            self.basket_id = basket_id
            self.add_event(self.ChangedId(basket_id=basket_id))

        def delete(self) -> None:
            self.add_event(self.Deleted(basket_id=self.basket_id))
"""

import zoneinfo
from dataclasses import dataclass, field
from datetime import datetime
from typing import TypeVar

A = TypeVar('A', bound='Aggregate')


@dataclass(frozen=True, kw_only=True)
class AggregateEvent:
    """Aggregate event."""

    occurred_on: datetime = field(default_factory=lambda: datetime.now(zoneinfo.ZoneInfo('UTC')))


@dataclass(kw_only=True)
class Aggregate:
    """Aggregate.

    Key characteristics:

    * Has ID.
    * Mutable.
    * May contain logic.
    * Can have nested VO, Entity, Aggregate.
    * Acts as transaction boundary.
    * Serves as root entity for context.
    * Has repository.
    """

    _events: list[AggregateEvent] = field(default_factory=list, init=False, repr=False, compare=False)

    def get_events(self) -> list[AggregateEvent]:
        return self._events

    def clear_events(self) -> None:
        self._events.clear()

    def add_event(self, event: AggregateEvent) -> None:
        self._events.append(event)


@dataclass(kw_only=True)
class Entity:
    """Entity.

    Key characteristics:

    * Has ID
    * Only mutable through aggregate
    * Cannot exist outside aggregate
    * Cannot be saved via repository (only as part of aggregate)
    * May contain logic
    """


@dataclass(frozen=True, kw_only=True)
class ValueObject:
    """Value object.

    Key characteristics:

    * No ID.
    * Immutable.
    * Can validate itself.
    * Can represent itself in different formats.
    """
