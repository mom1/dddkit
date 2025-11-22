from dddkit.exceptions import MissingDependencyError

try:
    import pydantic  # noqa: F401 # pyright: ignore[reportUnusedImport]
except ImportError as e:  # pragma: no cover
    raise MissingDependencyError('pydantic', 'pydantic', 'pydantic') from e

from .aggregates import Aggregate, AggregateEvent, Entity, ValueObject
from .changes_handler import ChangesHandler
from .events import DomainEvent, EventBroker
from .repositories import Repository

__all__ = (
    'Aggregate',
    'AggregateEvent',
    'ChangesHandler',
    'DomainEvent',
    'Entity',
    'EventBroker',
    'Repository',
    'ValueObject',
)
