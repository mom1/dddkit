from typing import cast
from uuid import uuid4

from .conftest import Basket, BasketId


class TestAggregate:
    def test_new_aggregate(self):
        basket = Basket.new(basket_id=cast(BasketId, uuid4()))

        assert (events := basket.get_events())
        assert isinstance(events[0], Basket.Created)

    def test_clear_events(self, basket: Basket) -> None:
        basket.delete()

        assert (events := basket.get_events())
        assert isinstance(events[0], Basket.Deleted)

        basket.clear_events()
        assert not basket.get_events()

    def test_add_event(self, basket: Basket) -> None:
        basket.change_id(cast(BasketId, uuid4()))

        assert (events := basket.get_events())
        assert isinstance(events[0], Basket.ChangedId)
        assert isinstance(events[0], Basket.Changed)
