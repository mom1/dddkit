from typing import cast
from uuid import uuid4

import pytest

from dddkit.dataclasses import ValueObject
from dddkit.dataclasses.aggregates import Entity, check
from dddkit.exceptions import CHECK_MUST_RETURN_BOOL_MSG, CheckFailedError, CheckMustReturnBoolError

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


class TestValueObject:
    class Point(ValueObject):
        lon: float
        lat: float

        @check()
        def lat_must_be_in_range(self) -> bool:
            return -90 <= self.lat <= 90

        @check
        def lon_must_be_in_range(self) -> tuple[bool, str]:
            return -180 <= self.lon <= 180, 'Longitude must be in the range -180 to 180'

        @check
        def lat_must_be_precision_to_4(self):
            return self.check_precision(self.lat, 4)

        @check
        def lon_must_be_precision_to_4(self):
            return self.check_precision(self.lon, 4)

        def check_precision(self, val: float, max_val: int) -> bool:
            s = f'{val:.5f}'
            decimal_part = s.rstrip('0').split('.')[-1]
            return len(decimal_part) <= max_val

    class PointError(ValueObject):
        lon: float
        lat: float

        @check  # pyright: ignore[reportArgumentType]
        def must_be_error(self) -> list:  # pyright: ignore[reportUnknownParameterType,reportMissingTypeArgument]
            return []  # pyright: ignore[reportUnknownVariableType]

    class PointCustomError(ValueObject):
        lon: float
        lat: float

        @check(exception_type=ValueError)
        def must_be_error(self) -> tuple[bool, str]:
            return False, 'Custom error message'

    @pytest.fixture
    def point(self) -> Point:
        return self.Point(lon=2.2945, lat=48.8584)

    def test_value_object(self) -> None:
        assert self.Point(lon=2.2945, lat=48.8584)

    def test_value_object_not_valid(self) -> None:
        with pytest.raises(CheckFailedError, match='Longitude must be in the range -180 to 180'):
            self.Point(lon=200.0, lat=48.8584)

    def test_value_object_with_invalid_check_return(self) -> None:
        with pytest.raises(CheckMustReturnBoolError, match=CHECK_MUST_RETURN_BOOL_MSG):
            self.PointError(lon=2.2945, lat=48.8584)

    def test_value_object_with_custom_error(self) -> None:
        with pytest.raises(ValueError, match='Custom error message'):
            self.PointCustomError(lon=2.2945, lat=48.8584)


class TestEntity:
    class Customer(Entity):
        first_name: str
        last_name: str
        age: int

        @check
        def customer_must_be_adult(self) -> bool:
            return self.age >= 18

    def test_entity_check(self):
        with pytest.raises(CheckFailedError, match='customer_must_be_adult'):
            self.Customer(first_name='Pete', last_name='Hodgson', age=17)
