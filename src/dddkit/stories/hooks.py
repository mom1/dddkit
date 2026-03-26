"""Hooks are needed to implement Domain Probe.

https://martinfowler.com/articles/domain-oriented-observability.html
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Literal

from typing_extensions import override

from .story import StepExecutionInfo, Story, StoryExecutionContext, logger


class StepStatus(Enum):
    RUNNING = '⟳'
    COMPLETED = '✓'
    FAILED = '✗'

    @override
    def __str__(self) -> str:
        return self.value


class ExecutionTimeTracker:
    __slots__: tuple[str, ...] = ('_start_times',)

    def __init__(self) -> None:
        self._start_times: dict[int, float] = {}

    def before(self, _: StoryExecutionContext, step_info: StepExecutionInfo) -> None:
        self._start_times[step_info.step_index] = time.perf_counter()

    def after(self, _: StoryExecutionContext, step_info: StepExecutionInfo) -> None:
        start_time = self._start_times.get(step_info.step_index) or 0
        step_info.meta['duration'] = step_info.meta.get('duration') or time.perf_counter() - start_time
        step_info.template = f'{step_info.template} [{{meta[duration]:.3f}}s]'

    def error(self, _: StoryExecutionContext, step_info: StepExecutionInfo) -> None:
        start_time = self._start_times.get(step_info.step_index) or 0
        step_info.meta['duration'] = time.perf_counter() - start_time


class StatusTracker:
    __slots__: tuple[str, ...] = ()

    def before(self, _: StoryExecutionContext, step_info: StepExecutionInfo) -> None:
        step_info.meta['status'] = StepStatus.RUNNING
        step_info.template = f'    {{meta[status]}}{step_info.template[4:]}'

    def after(self, _: StoryExecutionContext, step_info: StepExecutionInfo) -> None:
        if step_info.meta['status'] == StepStatus.RUNNING:
            step_info.meta['status'] = StepStatus.COMPLETED

    def error(self, _: StoryExecutionContext, step_info: StepExecutionInfo) -> None:
        step_info.meta['status'] = StepStatus.FAILED


class LoggingHook:
    __slots__: tuple[str, ...] = ()

    def before(self, context: StoryExecutionContext, _: StepExecutionInfo) -> None:
        logger.debug('\n%s', context)

    def after(self, context: StoryExecutionContext, step_info: StepExecutionInfo) -> None:
        if step_info.step_index == len(context.steps) - 1:
            logger.debug('\n%s', context)

    def error(self, context: StoryExecutionContext, _: StepExecutionInfo) -> None:
        logger.error('\n%s', context, exc_info=True)


def inject_hooks(story_cls: type[Story], hooks: list[object] | None = None) -> None:
    _hooks = hooks or [StatusTracker(), ExecutionTimeTracker(), LoggingHook()]

    hook_name: Literal['before', 'after', 'error']

    for hook_inst in _hooks:
        for hook_name in ('before', 'after', 'error'):
            if hook_handle := getattr(hook_inst, hook_name, None):
                story_cls.register_hook(hook_name, hook_handle)
