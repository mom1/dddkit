from __future__ import annotations

import logging
from asyncio import get_running_loop
from collections import defaultdict
from collections.abc import Awaitable, Callable, Generator, MutableMapping
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from inspect import iscoroutinefunction
from typing import Any, ClassVar, Literal, TypeAlias, TypeVar

from typing_extensions import override

ST = TypeVar('ST', bound='Story')
NameMethod: TypeAlias = str
HooksName: TypeAlias = Literal['before', 'after', 'error']
HOOKS_NAMES = {'before', 'after', 'error'}
Callback: TypeAlias = Callable[['StoryExecutionContext', 'StepExecutionInfo'], None]
logger = logging.getLogger(__name__)


class DefaultDict(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return ''


@dataclass(slots=True)
class StepExecutionInfo:
    step_name: NameMethod
    step_index: int
    error: Exception | None = None
    template: str = '    I.{step_name}'
    meta: dict[str, Any] = field(default_factory=DefaultDict)

    @override
    def __str__(self) -> str:
        return self.template.format_map(asdict(self, dict_factory=DefaultDict))


@dataclass(frozen=True, slots=True)
class StoryExecutionContext:
    story: Story
    steps: list[StepExecutionInfo] = field(default_factory=list)

    def __post_init__(self) -> None:
        story = self.story
        for idx, step_name in enumerate(story.I.__steps__):
            self.steps.append(StepExecutionInfo(step_name=step_name, step_index=idx))

    def __getitem__(self, index: int) -> StepExecutionInfo:
        return self.steps[index]

    @override
    def __str__(self) -> str:
        return '{class_name}:\n{steps}'.format(
            class_name=self.story.__class__.__name__, steps='\n'.join(map(str, self.steps))
        )


class Steps:
    __slots__: tuple[str, ...] = ('__steps__',)

    def __init__(self) -> None:
        self.__steps__: list[NameMethod] = []

    def __getattr__(self, name: NameMethod) -> None:
        if not name.startswith('_'):
            self.__steps__.append(name)


class _StoryType(type):
    @classmethod
    def __prepare__(cls, name: str, bases: tuple[type, ...], **kwargs: Any) -> MutableMapping[Literal['I'], Steps]:  # pyright: ignore[reportImplicitOverride,reportIncompatibleMethodOverride]
        return {'I': Steps()}


class Story(metaclass=_StoryType):
    __slots__: tuple[str, ...] = ()

    I: Steps  # noqa: E741

    __step_hooks__: ClassVar[dict[HooksName, list[Callback]]] = defaultdict(list)
    __context__cls__: ClassVar[type[StoryExecutionContext]] = StoryExecutionContext

    @classmethod
    def register_hook(cls, hook_type: HooksName, callback: Callback) -> None:
        if hook_type not in HOOKS_NAMES:
            raise ValueError(f'Unknown hook type: {hook_type}')
        cls.__step_hooks__[hook_type].append(callback)

    def __call__(self, state: object) -> Awaitable[None]:
        try:
            get_running_loop()
        except RuntimeError:
            if self._has_hooks:
                return self.__sync_call_with_hooks(state)  # pyright: ignore[reportReturnType]
            return self.__sync_call(state)  # pyright: ignore[reportReturnType]
        if self._has_hooks:
            return self.__async_call_with_hooks(state)
        return self.__async_call(state)

    @contextmanager
    def _step_context(
        self, idx: int, context: StoryExecutionContext
    ) -> Generator[tuple[StoryExecutionContext, StepExecutionInfo], Any, None]:
        step_info = context[idx]

        try:
            for hook in self.__step_hooks__.get('before') or []:
                hook(context, step_info)
            yield context, step_info
        except Exception as e:
            step_info.error = e
            for hook in self.__step_hooks__.get('error') or []:
                hook(context, step_info)
            raise
        finally:
            for hook in self.__step_hooks__.get('after') or []:
                hook(context, step_info)

    @property
    def _has_hooks(self) -> bool:
        return next((True for i in self.__step_hooks__.values() if i), False)

    def __sync_call(self, state: object) -> None:
        for step in self.I.__steps__:
            getattr(self, step)(state)

    def __sync_call_with_hooks(self, state: object) -> None:
        context = self.__context__cls__(story=self)
        for idx, step in enumerate(self.I.__steps__):
            method = getattr(self, step)
            with self._step_context(idx, context):
                method(state)

    async def __async_call(self, state: object) -> None:
        for step in self.I.__steps__:
            method = getattr(self, step)
            if iscoroutinefunction(method):
                await method(state)
            else:
                method(state)

    async def __async_call_with_hooks(self, state: object) -> None:
        context = self.__context__cls__(story=self)
        for idx, step in enumerate(self.I.__steps__):
            method = getattr(self, step)
            with self._step_context(idx, context):
                if iscoroutinefunction(method):
                    await method(state)
                else:
                    method(state)
