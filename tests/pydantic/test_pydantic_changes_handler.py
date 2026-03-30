from functools import singledispatchmethod
from typing import Any, NamedTuple, cast
from uuid import uuid4

from typing_extensions import override

from dddkit.pydantic import AggregateEvent, ChangesHandler, DomainEvent

from .conftest import Basket, BasketChanged, BasketFactory, BasketId


class ChangeResult(NamedTuple):
    """Result of processing basket changes."""

    created_fields: dict[str, Any] = {}
    updated_fields: dict[str, Any] = {}
    deleted_id: list[BasketId] = []
    domain_events: list[DomainEvent] = []


class BasketChangesHandler(ChangesHandler[Basket, ChangeResult]):
    """Handler for basket aggregate changes."""

    _slots__: tuple[str, ...] = ('created_fields', 'updated_fields', 'deleted_id', 'domain_events')
    result_type: type[ChangeResult] = ChangeResult

    @override
    def _clear_state(self) -> None:
        self.created_fields: dict[str, Any] = {}
        self.updated_fields: dict[str, Any] = {}
        self.deleted_id: list[BasketId] = []
        self.domain_events: list[DomainEvent] = []

    @singledispatchmethod
    def handle_changes(self, event: AggregateEvent, basket: Basket) -> None:
        raise NotImplementedError(f'Has no handler for event {event!r}')

    @handle_changes.register
    def _(self, _: Basket.Created, basket: Basket) -> None:
        self.created_fields['id'] = basket.basket_id

    @handle_changes.register
    def _(self, event: Basket.ChangedId, _: Basket) -> None:
        self.updated_fields['id'] = event.basket_id
        self.domain_events.append(BasketChanged(basket_id=event.basket_id))

    @handle_changes.register
    def _(self, _: Basket.Deleted, basket: Basket) -> None:
        self.deleted_id.append(basket.basket_id)


def test_when_basket_created_then_handler_records_created_field(basket_factory: type[BasketFactory]):
    """Created event results in recording basket ID in created_fields."""
    basket = basket_factory.created()
    handler = BasketChangesHandler()

    with handler as hc:
        result = hc(basket)

    assert result.created_fields == {'id': basket.basket_id}


def test_when_basket_id_changed_then_handler_records_update_and_emits_event(basket_factory: type[BasketFactory]):
    """ChangedId event results in recording update and emitting domain event."""
    basket = basket_factory.build()
    handler = BasketChangesHandler()
    new_id = cast(BasketId, uuid4())
    basket.change_id(new_id)

    with handler as hc:
        result = hc(basket)

    assert result.updated_fields == {'id': new_id}
    assert len(result.domain_events) == 1
    assert isinstance(result.domain_events[0], BasketChanged)
    assert result.domain_events[0].basket_id == new_id


def test_when_basket_deleted_then_handler_records_deleted_id(basket_factory: type[BasketFactory]):
    """Deleted event results in recording basket ID for deletion."""
    basket = basket_factory.build()
    handler = BasketChangesHandler()
    basket.delete()

    with handler as hc:
        result = hc(basket)

    assert result.deleted_id == [basket.basket_id]


def test_given_multiple_events_when_handled_then_all_processed(basket_factory: type[BasketFactory]):
    """Handler processes all pending events in aggregate."""
    basket = basket_factory.build()
    handler = BasketChangesHandler()
    new_id = cast(BasketId, uuid4())

    basket.change_id(new_id)
    basket.delete()

    with handler as hc:
        result = hc(basket)

    assert result.updated_fields == {'id': new_id}
    assert result.deleted_id == [basket.basket_id]
    assert len(result.domain_events) == 1


def test_when_context_exits_then_handler_state_cleared(basket_factory: type[BasketFactory]):
    """Handler state is cleared after context manager exits."""
    basket = basket_factory.build()
    handler = BasketChangesHandler()
    basket.change_id(cast(BasketId, uuid4()))

    with handler as hc:
        hc(basket)
        assert handler.updated_fields

    assert not handler.updated_fields
    assert not handler.domain_events


def test_given_cleared_events_when_handled_then_no_result(basket_factory: type[BasketFactory]):
    """Aggregate with cleared events produces empty result."""
    basket = basket_factory.build()
    handler = BasketChangesHandler()
    basket.change_id(cast(BasketId, uuid4()))
    basket.clear_events()

    with handler as hc:
        result = hc(basket)

    assert not result.updated_fields
    assert not result.domain_events
