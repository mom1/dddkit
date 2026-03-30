from typing import cast
from uuid import uuid4

from .conftest import Basket, BasketFactory, BasketId


def test_when_aggregate_created_via_factory_then_created_event_emitted(
    basket_factory: type[BasketFactory],
):
    """Using factory method adds Created event to aggregate's event list."""
    basket = basket_factory.created()

    events = basket.get_events()
    assert len(events) == 1
    assert isinstance(events[0], Basket.Created)


def test_when_aggregate_created_directly_then_no_events(
    basket_factory: type[BasketFactory],
):
    """Direct instantiation does not emit domain events."""
    basket = basket_factory.build()

    assert not basket.get_events()


def test_when_aggregate_modified_then_domain_event_added(
    basket_factory: type[BasketFactory],
):
    """Changing aggregate state adds corresponding domain event."""
    basket = basket_factory.build()
    new_id = cast(BasketId, uuid4())

    basket.change_id(new_id)

    events = basket.get_events()
    assert len(events) == 1
    assert isinstance(events[0], Basket.ChangedId)
    assert events[0].basket_id == new_id


def test_when_aggregate_deleted_then_deleted_event_added(
    basket_factory: type[BasketFactory],
):
    """Delete operation adds Deleted event to aggregate."""
    basket = basket_factory.build()

    basket.delete()

    events = basket.get_events()
    assert len(events) == 1
    assert isinstance(events[0], Basket.Deleted)


def test_when_events_cleared_then_aggregate_has_no_events(
    basket_factory: type[BasketFactory],
):
    """clear_events removes all pending domain events from aggregate."""
    basket = basket_factory.created()
    basket.delete()
    assert len(basket.get_events()) == 2

    basket.clear_events()

    assert not basket.get_events()


def test_when_event_is_subtype_then_matches_parent_type(
    basket_factory: type[BasketFactory],
):
    """Domain events maintain proper inheritance hierarchy."""
    basket = basket_factory.build()
    new_id = cast(BasketId, uuid4())

    basket.change_id(new_id)

    events = basket.get_events()
    assert isinstance(events[0], Basket.Changed)
    assert isinstance(events[0], Basket.ChangedId)
