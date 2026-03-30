from typing import Any

import pytest
from _pytest.logging import LogCaptureFixture

from dddkit.stories import ExecutionTimeTracker, LoggingHook, StatusTracker, StepExecutionInfo, StoryExecutionContext
from dddkit.stories.hooks import StepStatus, inject_hooks

from .conftest import SampleStory, StoryWithError


def test_when_story_executed_then_execution_time_recorded_for_each_step(
    sample_story: SampleStory,
):
    """ExecutionTimeTracker adds duration to each step's meta after completion."""
    tracker = ExecutionTimeTracker()
    context_collector: list[StoryExecutionContext] = []

    def capture_context(context: StoryExecutionContext, _: Any) -> None:
        context_collector.append(context)

    sample_story.register_hook('after', capture_context)
    sample_story.register_hook('after', tracker.after)

    state = sample_story.State()
    sample_story(state)

    context = context_collector[0]
    for step in context.steps:
        assert 'duration' in step.meta
        assert isinstance(step.meta['duration'], float)
        assert step.meta['duration'] >= 0


def test_given_error_in_step_when_story_executed_then_duration_recorded_for_failed_step(
    story_with_error: StoryWithError,
):
    """ExecutionTimeTracker records duration even for steps that raise errors."""
    tracker = ExecutionTimeTracker()
    context_collector: list[StoryExecutionContext] = []

    def capture_context(context: StoryExecutionContext, _: Any) -> None:
        context_collector.append(context)

    story_with_error.register_hook('after', capture_context)
    story_with_error.register_hook('error', capture_context)
    story_with_error.register_hook('after', tracker.after)
    story_with_error.register_hook('error', tracker.error)

    state = story_with_error.State()
    with pytest.raises(ValueError, match='An error occurred'):
        story_with_error(state)

    context = context_collector[-1]
    failed_step = context.steps[1]
    assert 'duration' in failed_step.meta
    assert isinstance(failed_step.meta['duration'], float)


def test_when_step_template_customized_then_shows_duration_in_output(
    sample_story: SampleStory,
):
    """Custom template with duration placeholder formats correctly."""
    tracker = ExecutionTimeTracker()
    context_collector: list[StoryExecutionContext] = []

    def capture_context(context: StoryExecutionContext, _: Any) -> None:
        context_collector.append(context)

    sample_story.register_hook('after', capture_context)
    sample_story.register_hook('after', tracker.after)

    state = sample_story.State()
    sample_story(state)

    context = context_collector[0]
    for step in context.steps:
        step_str = str(step)
        assert '[0.' in step_str or step_str.endswith('s]')


def test_when_story_executes_successfully_then_all_steps_marked_completed(
    sample_story: SampleStory,
):
    """StatusTracker marks all steps as COMPLETED after successful execution."""
    tracker = StatusTracker()
    context_collector: list[StoryExecutionContext] = []

    def capture_context(context: StoryExecutionContext, _: Any) -> None:
        context_collector.append(context)

    sample_story.register_hook('before', tracker.before)
    sample_story.register_hook('after', tracker.after)
    sample_story.register_hook('after', capture_context)

    state = sample_story.State()
    sample_story(state)

    context = context_collector[-1]
    for step in context.steps:
        assert step.meta['status'] == StepStatus.COMPLETED


def test_given_error_in_step_when_story_executes_then_failed_step_marked_failed(
    story_with_error: StoryWithError,
):
    """StatusTracker marks failed step as FAILED while previous remain COMPLETED."""
    tracker = StatusTracker()
    context_collector: list[StoryExecutionContext] = []

    def capture_context(context: StoryExecutionContext, _: Any) -> None:
        context_collector.append(context)

    story_with_error.register_hook('before', tracker.before)
    story_with_error.register_hook('after', tracker.after)
    story_with_error.register_hook('error', tracker.error)
    story_with_error.register_hook('after', capture_context)
    story_with_error.register_hook('error', capture_context)

    state = story_with_error.State()
    with pytest.raises(ValueError, match='An error occurred'):
        story_with_error(state)

    context = context_collector[-1]
    assert context.steps[0].meta['status'] == StepStatus.COMPLETED
    assert context.steps[1].meta['status'] == StepStatus.FAILED


def test_when_step_template_customized_then_shows_status_in_output(
    sample_story: SampleStory,
):
    """Custom template with status placeholder formats correctly."""
    tracker = StatusTracker()
    context_collector: list[StoryExecutionContext] = []

    def capture_context(context: StoryExecutionContext, _: Any) -> None:
        context_collector.append(context)

    sample_story.register_hook('before', tracker.before)
    sample_story.register_hook('after', tracker.after)
    sample_story.register_hook('after', capture_context)

    state = sample_story.State()
    sample_story(state)

    context = context_collector[-1]
    for step in context.steps:
        step_str = str(step)
        assert StepStatus.COMPLETED.value in step_str


def test_when_story_executes_then_debug_log_contains_context(
    sample_story: SampleStory,
    caplog: LogCaptureFixture,
):
    """LoggingHook outputs context representation at DEBUG level."""
    hook = LoggingHook()
    sample_story.register_hook('before', hook.before)
    sample_story.register_hook('after', hook.after)

    with caplog.at_level('DEBUG'):
        state = sample_story.State()
        sample_story(state)

    debug_logs = [r for r in caplog.records if r.levelname == 'DEBUG']
    assert len(debug_logs) >= 1
    assert sample_story.__class__.__name__ in caplog.text


def test_given_error_in_step_when_story_executes_then_error_log_contains_error(
    story_with_error: StoryWithError,
    caplog: LogCaptureFixture,
):
    """LoggingHook outputs error information at ERROR level."""
    hook = LoggingHook()
    story_with_error.register_hook('before', hook.before)
    story_with_error.register_hook('after', hook.after)
    story_with_error.register_hook('error', hook.error)

    with caplog.at_level('ERROR'):
        state = story_with_error.State()
        with pytest.raises(ValueError, match='An error occurred'):
            story_with_error(state)

    error_logs = [r for r in caplog.records if r.levelname == 'ERROR']
    assert len(error_logs) >= 1


def test_when_inject_hooks_called_then_default_hooks_registered(
    sample_story: SampleStory,
):
    """inject_hooks registers ExecutionTimeTracker, StatusTracker, and LoggingHook."""
    assert not sample_story.__class__.__step_hooks__

    inject_hooks(sample_story.__class__)

    assert len(sample_story.__step_hooks__['before']) == 3
    assert len(sample_story.__step_hooks__['after']) == 3
    assert len(sample_story.__step_hooks__['error']) == 3

    state = sample_story.State(step_one=False, step_two=False, step_three=False)
    sample_story(state)

    assert state.step_one
    assert state.step_two
    assert state.step_three


def test_when_inject_hooks_with_custom_hooks_then_only_custom_hooks_registered(
    sample_story: SampleStory,
):
    """inject_hooks with custom hooks list registers only provided hooks."""
    assert not sample_story.__class__.__step_hooks__

    class CustomHook:
        def __init__(self) -> None:
            self.before_called: int = 0
            self.after_called: int = 0
            self.error_called: int = 0

        def before(self, _: StoryExecutionContext, __: StepExecutionInfo) -> None:
            self.before_called += 1

        def after(self, _: StoryExecutionContext, __: StepExecutionInfo) -> None:
            self.after_called += 1

        def error(self, _: StoryExecutionContext, __: StepExecutionInfo) -> None:
            self.error_called += 1

    custom_hook = CustomHook()
    inject_hooks(sample_story.__class__, hooks=[custom_hook])

    assert len(sample_story.__step_hooks__['before']) == 1
    assert len(sample_story.__step_hooks__['after']) == 1
    assert len(sample_story.__step_hooks__['error']) == 1

    state = sample_story.State(step_one=False, step_two=False, step_three=False)
    sample_story(state)

    assert custom_hook.before_called == 3
    assert custom_hook.after_called == 3
    assert custom_hook.error_called == 0


def test_given_error_scenario_when_inject_hooks_then_error_hook_called(
    story_with_error: StoryWithError,
):
    """inject_hooks with custom hook calls error handler on exception."""
    assert not story_with_error.__class__.__step_hooks__

    class ErrorHook:
        def __init__(self) -> None:
            self.error_called: bool = False

        def before(self, _: StoryExecutionContext, __: StepExecutionInfo) -> None:
            pass

        def after(self, _: StoryExecutionContext, __: StepExecutionInfo) -> None:
            pass

        def error(self, _: StoryExecutionContext, __: StepExecutionInfo) -> None:
            self.error_called = True

    error_hook = ErrorHook()
    inject_hooks(story_with_error.__class__, hooks=[error_hook])

    state = story_with_error.State(step_one=False)
    with pytest.raises(ValueError, match='An error occurred'):
        story_with_error(state)

    assert error_hook.error_called
    assert state.step_one


def test_given_partial_hook_methods_when_inject_hooks_then_only_available_methods_registered(
    sample_story: SampleStory,
):
    """inject_hooks works with hooks that only implement some methods."""
    assert not sample_story.__class__.__step_hooks__

    class PartialHook:
        def __init__(self) -> None:
            self.before_called: int = 0

        def before(self, _: StoryExecutionContext, __: Any) -> None:
            self.before_called += 1

    partial_hook = PartialHook()
    inject_hooks(sample_story.__class__, hooks=[partial_hook])

    assert len(sample_story.__step_hooks__['before']) == 1
    assert len(sample_story.__step_hooks__['after']) == 0
    assert len(sample_story.__step_hooks__['error']) == 0

    state = sample_story.State(step_one=False, step_two=False, step_three=False)
    sample_story(state)

    assert partial_hook.before_called == 3
    assert state.step_one
    assert state.step_two
    assert state.step_three
