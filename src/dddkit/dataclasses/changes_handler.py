"""Module for handling events in aggregate.

Example:
-------
    from functools import singledispatchmethod
    from dddkit.dataclasses import Aggregate, AggregateEvent, ChangesHandler

    BasketId = NewType('BasketId', UUID)

    class Basket(Aggregate):
        basket_id: BasketId
        ...

    class Result(NamedTuple):
        created_fields: dict[str, Any] = {}
        updated_fields: dict[str, Any] = {}
        deleted_id: list[BasketId] = []
        domain_events: list[AggregateEvent] = []

    class BasketChangesHandler(ChangesHandler[Basket, Result]):
        _slots__ = ('created_fields', 'updated_fields', 'deleted_id', 'domain_events')

        result_type = Result

        def _clear_state(self) -> None:
            self.created_fields: dict[str, Any] = {}
            self.updated_fields: dict[str, Any] = {}
            self.deleted_id: list[BasketId] = []
            self.domain_events: list[AggregateEvent] = []

        @singledispatchmethod
        def handle_changes(self, event: AggregateEvent, basket: Basket) -> None:
            raise NotImplementedError(f'Has no handler for event {event!r}')

        @handle_changes.register
        def _(self, _: Basket.Created, basket: Basket) -> None:
            self.created_fields['id'] = basket.basket_id

        @handle_changes.register
        def _(self, event: Basket.ChangedId, _: Basket) -> None:
            self.updated_fields['id'] = event.basket_id

        @handle_changes.register
        def _(self, _: Basket.Deleted, basket: Basket) -> None:
            self.deleted_id.append(basket.basket_id)
"""

from functools import singledispatchmethod
from types import TracebackType
from typing import Any, Generic, NamedTuple, TypeVar

from typing_extensions import Self

from .aggregates import Aggregate, AggregateEvent

T = TypeVar('T', bound=Aggregate)
Result = TypeVar('Result', bound=NamedTuple)


class ChangesHandler(Generic[T, Result]):
    """Base class for handling events in aggregate."""

    __slots__: tuple[str, ...] = ()
    result_type: Any

    def __init__(self) -> None:
        self._clear_state()

    def _clear_state(self) -> None:
        raise NotImplementedError

    def __call__(self, aggregate: T) -> Result:
        for e in aggregate.get_events():
            self.handle_changes(e, aggregate)
        aggregate.clear_events()
        return self.result_type(*(getattr(self, k, None) for k in self.result_type._fields))

    def __enter__(self) -> Self:
        self._clear_state()
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
    ) -> None:
        self._clear_state()

    @singledispatchmethod
    def handle_changes(self, event: AggregateEvent, _: T) -> None:
        """Handle changes in aggregate."""
        raise NotImplementedError
