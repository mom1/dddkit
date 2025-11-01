"""Repository protocols.

Example:
-------
    from dddkit.pydantic import Repository

    BasketId = NewType('BasketId', UUID)

    class Basket(Aggregate):
        basket_id: BasketId

    class InMemoryBasketRepository(Repository[Basket, BasketId]):
        '''Repository implementation that stores aggregates in memory'''

        def __init__(self, handle_changes: ChangesHandler | None = None):
            self.aggregates: dict[BasketId, Basket] = {}
            self.handle_changes = handle_changes or ChangesHandler()

        async def save(self, basket: Basket) -> None:
            with self.handle_changes as hc:
                result = hc(basket)

                # It is highly recommended to do everything in a transaction since Aggregate is the transaction boundary
                async with in_transaction():
                    if create_fields := result.create_fields:
                        # ORM logic for creating a record
                        self.aggregates[basket.id] = basket

                    if update_fields := result.update_fields:
                        # ORM logic for updating a record
                        self.aggregates.pop(basket.id)
                        self.aggregates[basket.id] = basket

                    if ids := result.deleted_id:
                        # ORM logic for deleting a record
                        for id in ids:
                            self.aggregates.pop(basket_id, None):

                    for event in result.domain_events:
                        await handle_event(event)


        async def get(self, basket_id: BasketId) -> Basket | None:
            return self.aggregates.get(basket_id)

        async def delete(self, basket_id: BasketId) -> None:
            self.aggregates.pop(basket_id, None):
"""

from typing import Protocol, TypeVar

from .aggregates import Aggregate

T = TypeVar('T', bound=Aggregate)
T_ID_contra = TypeVar('T_ID_contra', contravariant=True)


class Repository(Protocol[T, T_ID_contra]):
    """DDD repository protocol.

    Focused on the persistence mechanism.
    """

    async def save(self, aggregate: T) -> None:
        """Saves aggregate to repository."""

    async def get(self, aggregate_id: T_ID_contra) -> T | None:
        """Returns aggregate by its identifier."""

    async def delete(self, aggregate: T) -> None:
        """Deletes aggregate from repository."""
