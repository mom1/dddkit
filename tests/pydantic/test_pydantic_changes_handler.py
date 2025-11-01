from functools import singledispatchmethod
from typing import Any, NamedTuple, cast
from uuid import uuid4

from typing_extensions import override

from dddkit.pydantic import AggregateEvent, ChangesHandler, DomainEvent

from .conftest import Basket, BasketChanged, BasketId


class Result(NamedTuple):
    created_fields: dict[str, Any] = {}
    updated_fields: dict[str, Any] = {}
    deleted_id: list[BasketId] = []
    domain_events: list[DomainEvent] = []


class BasketChangesHandler(ChangesHandler[Basket, Result]):
    _slots__: tuple[str, ...] = ('created_fields', 'updated_fields', 'deleted_id', 'domain_events')

    result_type: type[Result] = Result

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


class TestChangeHandler:
    def test_handle_changes(self, basket: Basket):
        basket_changes_handler = BasketChangesHandler()
        basket_changes_handler.created_fields = {'id': cast(BasketId, uuid4())}

        new_basket_id = cast(BasketId, uuid4())
        basket.change_id(new_basket_id)

        with basket_changes_handler as hc:
            assert not hc.created_fields

            result = hc(basket)

            assert result.updated_fields == {'id': new_basket_id}

            assert result.domain_events
            assert basket_changes_handler.domain_events
            assert isinstance(result.domain_events[0], BasketChanged)

        assert result.updated_fields
        assert not basket_changes_handler.updated_fields
