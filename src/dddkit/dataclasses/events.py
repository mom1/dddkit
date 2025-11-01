from asyncio import get_running_loop, iscoroutinefunction
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import TypeAlias, TypeVar
from uuid import UUID
from zoneinfo import ZoneInfo

try:
    from uuid import uuid7 as uuid_factory  # pyright: ignore[reportAttributeAccessIssue,reportUnknownVariableType]
except ImportError:
    from uuid import uuid4 as uuid_factory

uuid_factory: Callable[[], UUID]

ET = TypeVar('ET', bound='DomainEvent')

HandlerEvent: TypeAlias = Callable[..., None] | Callable[..., Awaitable[None]]
Predicate: TypeAlias = Callable[['DomainEvent'], bool]


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    """Base event."""

    version: int = 1
    id: UUID = field(default_factory=uuid_factory)  # pyright: ignore[reportUnknownArgumentType]
    occurred_on: datetime = field(default_factory=lambda: datetime.now(ZoneInfo('UTC')))


class EventBroker:
    __slots__: tuple[str, ...] = ('_event_handlers',)

    def __init__(self) -> None:
        self._event_handlers: dict[Predicate, set[HandlerEvent]] = {}

    def __call__(self, event: DomainEvent) -> Awaitable[None]:
        try:
            get_running_loop()
            return self.async_publish(event)
        except RuntimeError:
            return self.publish(event)  # pyright: ignore[reportReturnType]

    def subscribe(self, event_predicate: Predicate, subscriber: HandlerEvent) -> None:
        """Subscribe to events."""
        subscribers = self._event_handlers.setdefault(event_predicate, set())
        subscribers.add(subscriber)

    def register(self, event_predicate: Predicate) -> Callable[..., HandlerEvent]:
        """Register handler subscription to events."""

        def decorator(func: HandlerEvent) -> HandlerEvent:
            self.subscribe(event_predicate, func)
            return func

        return decorator

    def unsubscribe(
        self, event_predicate: Predicate, subscriber: Callable[[ET], None] | Callable[[ET], Awaitable[None]]
    ) -> None:
        """Unsubscribe from event."""
        if subscribers := self._event_handlers.get(event_predicate):
            subscribers.discard(subscriber)

    def _get_subscribers(self, event: DomainEvent) -> set[HandlerEvent]:
        """Send event to all subscribers.

        Each subscriber will receive each event only once, even if it was subscribed multiple times, possibly with
        different predicates.
        """
        matching_handlers: set[HandlerEvent] = set()
        for event_predicate, handlers in self._event_handlers.items():
            if event_predicate(event):
                matching_handlers |= handlers

        if not matching_handlers:
            raise NotImplementedError(f'No suitable event handlers found. {event!r}')

        return matching_handlers

    def publish(self, event: DomainEvent) -> None:
        for handler in self._get_subscribers(event):
            handler(event)

    async def async_publish(self, event: DomainEvent) -> None:
        for handler in self._get_subscribers(event):
            if iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)

    def instance(self, obj_type: type[ET] | tuple[type[ET], ...] | None) -> Callable[[HandlerEvent], HandlerEvent]:
        _type = obj_type if obj_type is not None else type(None)

        def decorator(func: HandlerEvent) -> HandlerEvent:
            self.subscribe(lambda e: isinstance(e, _type), func)
            return func

        return decorator
