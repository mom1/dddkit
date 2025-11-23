"""Module for basic aggregate classes.

Example:
-------
    from dddkit.dataclasses import Aggregate

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

import inspect
import zoneinfo
from collections.abc import Callable, Generator
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
from types import SimpleNamespace
from typing import ParamSpec, TypeVar, cast

from dddkit.exceptions import CheckFailedError, CheckMustReturnBoolError

P = ParamSpec('P')
R = bool | tuple[bool, str]
T = TypeVar('T', bound=Callable[..., R])


@dataclass(frozen=True, kw_only=True)
class AggregateEvent:
    """Aggregate event."""

    occurred_on: datetime = field(default_factory=lambda: datetime.now(zoneinfo.ZoneInfo('UTC')))

    def __init_subclass__(cls) -> None:
        dataclass(cls, frozen=True, kw_only=True)


class CheckableObject(SimpleNamespace):
    def __post_init__(self) -> None:
        self.__check()

    def __check(self) -> None:
        for _check in self.__obtain_checks():
            _check()

    def __obtain_checks(self) -> Generator[Callable[..., bool | tuple[bool, str]], None, None]:
        for _method_name, method in inspect.getmembers(
            self, predicate=lambda v: inspect.ismethod(v) and not v.__name__.startswith('_')
        ):
            if getattr(method, '_check', False):
                yield cast(Callable[..., bool | tuple[bool, str]], method)


@dataclass(kw_only=True)
class Aggregate(CheckableObject):
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

    def __init_subclass__(cls) -> None:
        dataclass(cls, kw_only=True)

    def get_events(self) -> list[AggregateEvent]:
        return self._events

    def clear_events(self) -> None:
        self._events.clear()

    def add_event(self, event: AggregateEvent) -> None:
        self._events.append(event)


class Entity(CheckableObject):
    """Entity.

    Key characteristics:

    * Has ID
    * Only mutable through aggregate
    * Cannot exist outside aggregate
    * Cannot be saved via repository (only as part of aggregate)
    * May contain logic
    """

    def __init_subclass__(cls) -> None:
        dataclass(cls, kw_only=True)


class ValueObject(CheckableObject):
    """Value object.

    Key characteristics:

    * No ID.
    * Immutable.
    * Can validate itself.
    * Can represent itself in different formats.
    """

    def __init_subclass__(cls) -> None:
        dataclass(cls, frozen=True, kw_only=True)


def check(func: T | None = None, *, exception_type: type[Exception] | None = None) -> Callable[[T], T] | T:
    def decorator(f: T) -> T:
        @wraps(f)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            result = f(*args, **kwargs)
            message = ''

            if isinstance(result, tuple):
                result, message = result

            if not isinstance(result, bool):
                raise CheckMustReturnBoolError

            if not result:
                if exception_type:
                    raise exception_type(message)
                raise CheckFailedError(message or f'Check failed: {f.__name__}')

            return result

        wrapper._check = True  # pyright: ignore[reportAttributeAccessIssue]

        return wrapper  # pyright: ignore[reportReturnType]

    if func is None:
        return decorator
    return decorator(func)
