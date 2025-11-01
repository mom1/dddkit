"""Module for basic aggregate classes.

Example:
-------
    from dddkit.pydantic.aggregates import Aggregate

    BasketId = NewType('BasketId', UUID)

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
from datetime import datetime
from typing import ClassVar, TypeVar

from pydantic import BaseModel, ConfigDict, Field

A = TypeVar('A', bound='Aggregate')


class AggregateEvent(BaseModel):
    """Aggregate event."""

    occurred_on: datetime = Field(default_factory=lambda: datetime.now(zoneinfo.ZoneInfo('UTC')))

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)


class Aggregate(BaseModel):
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

    _events: list[AggregateEvent] = []
    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True, validate_assignment=True)

    def get_events(self) -> list[AggregateEvent]:
        return self._events

    def clear_events(self) -> None:
        self._events.clear()

    def add_event(self, event: AggregateEvent) -> None:
        self._events.append(event)


class Entity(BaseModel):
    """Entity.

    Key characteristics:

    * Has ID
    * Only mutable through aggregate
    * Cannot exist outside aggregate
    * Cannot be saved via repository (only as part of aggregate)
    * May contain logic
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)


class ValueObject(BaseModel):
    """Value object.

    Key characteristics:

    * No ID.
    * Immutable.
    * Can validate itself.
    * Can represent itself in different formats.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True, frozen=True)
