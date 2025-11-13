from typing import cast

import pytest
from _pytest.logging import LogCaptureFixture

from dddkit.stories import ExecutionTimeTracker, LoggingHook, StatusTracker, StepExecutionInfo, StoryExecutionContext
from dddkit.stories.hooks import StepStatus, inject_hooks
from tests.stories.conftest import SampleStory, StoryWithError


class TestExecutionTimeTracker:
    def test_execution_time_tracker(self, sample_story: SampleStory) -> None:
        tracker = ExecutionTimeTracker()
        ctx: StoryExecutionContext | None = None

        def hook_wrap(context: StoryExecutionContext, step_info: StepExecutionInfo) -> None:
            nonlocal ctx

            ctx = context
            tracker.before(context, step_info)

        sample_story.register_hook('before', hook_wrap)
        sample_story.register_hook('after', tracker.after)
        sample_story.register_hook('error', tracker.error)

        state = sample_story.State()
        sample_story(state)

        assert ctx
        for step_info in cast(list[StepExecutionInfo], ctx.steps):
            assert 'duration' in step_info.meta
            assert isinstance(step_info.meta['duration'], float)
            assert step_info.template.endswith('[{meta[duration]:.3f}s]')
            assert str(step_info) == f'    I.{step_info.step_name} [{step_info.meta["duration"]:.3f}s]'

    def test_execution_time_tracker_error(self, story_with_error: StoryWithError) -> None:
        tracker = ExecutionTimeTracker()
        ctx: StoryExecutionContext | None = None

        def hook_wrap(context: StoryExecutionContext, step_info: StepExecutionInfo) -> None:
            nonlocal ctx

            ctx = context
            tracker.before(context, step_info)

        story_with_error.register_hook('before', hook_wrap)
        story_with_error.register_hook('after', tracker.after)
        story_with_error.register_hook('error', tracker.error)

        state = story_with_error.State()
        with pytest.raises(ValueError, match='An error occurred'):
            story_with_error(state)

        assert ctx
        assert 'duration' in ctx[1].meta
        assert isinstance(ctx[1].meta['duration'], float)
        assert ctx[1].meta['duration'] >= 0


class TestStatusTracker:
    def test_status_tracker(self, sample_story: SampleStory):
        tracker = StatusTracker()
        ctx: StoryExecutionContext | None = None

        def hook_wrap(context: StoryExecutionContext, step_info: StepExecutionInfo) -> None:
            nonlocal ctx

            ctx = context
            tracker.before(context, step_info)

        sample_story.register_hook('before', hook_wrap)
        sample_story.register_hook('after', tracker.after)
        sample_story.register_hook('error', tracker.error)

        state = sample_story.State()
        sample_story(state)

        assert ctx
        for step_info in cast(list[StepExecutionInfo], ctx.steps):
            assert step_info.meta['status'] == StepStatus.COMPLETED
            assert step_info.template.startswith('    {meta[status]}')
            assert str(step_info) == f'    {step_info.meta["status"]}I.{step_info.step_name}'

    def test_status_tracker_with_error(self, story_with_error: StoryWithError):
        tracker = StatusTracker()
        ctx: StoryExecutionContext | None = None

        def hook_wrap(context: StoryExecutionContext, step_info: StepExecutionInfo) -> None:
            nonlocal ctx

            ctx = context
            tracker.before(context, step_info)

        story_with_error.register_hook('before', hook_wrap)
        story_with_error.register_hook('after', tracker.after)
        story_with_error.register_hook('error', tracker.error)

        state = story_with_error.State()
        with pytest.raises(ValueError, match='An error occurred'):
            story_with_error(state)

        assert ctx
        assert ctx[0].meta
        assert ctx[0].meta['status'] == StepStatus.COMPLETED
        assert ctx[1].meta['status'] == StepStatus.FAILED


class TestLoggingHook:
    def test_logging_hook(self, sample_story: SampleStory, caplog: LogCaptureFixture):
        hook = LoggingHook()
        ctx: StoryExecutionContext | None = None

        def hook_wrap(context: StoryExecutionContext, step_info: StepExecutionInfo) -> None:
            nonlocal ctx

            ctx = context
            hook.before(context, step_info)

        sample_story.register_hook('before', hook_wrap)
        sample_story.register_hook('after', hook.after)
        sample_story.register_hook('error', hook.error)

        with caplog.at_level('DEBUG'):
            state = sample_story.State()
            sample_story(state)

        debug_logs = [record for record in caplog.records if record.levelname == 'DEBUG']
        assert len(debug_logs) >= 1
        assert str(ctx) in caplog.text

    def test_logging_hook_with_error(self, story_with_error: StoryWithError, caplog: LogCaptureFixture):
        hook = LoggingHook()
        story_with_error.register_hook('before', hook.before)
        story_with_error.register_hook('after', hook.after)
        story_with_error.register_hook('error', hook.error)

        with caplog.at_level('ERROR'):
            state = story_with_error.State()
            with pytest.raises(ValueError, match='An error occurred'):
                story_with_error(state)

        error_logs = [record for record in caplog.records if record.levelname == 'ERROR']
        assert len(error_logs) >= 1


class TestInjectHooks:
    def test_inject_hooks_with_default_hooks(self, sample_story: SampleStory):
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

    def test_inject_hooks_with_custom_hooks(self, sample_story: SampleStory):
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

        assert state.step_one
        assert state.step_two
        assert state.step_three

    def test_inject_hooks_with_error_scenario(self, story_with_error: StoryWithError):
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

        assert len(story_with_error.__step_hooks__['before']) == 1
        assert len(story_with_error.__step_hooks__['after']) == 1
        assert len(story_with_error.__step_hooks__['error']) == 1

        state = story_with_error.State(step_one=False)
        with pytest.raises(ValueError, match='An error occurred'):
            story_with_error(state)

        assert error_hook.error_called
        assert state.step_one

    def test_inject_hooks_partial_hook_methods(self, sample_story: SampleStory):
        assert not sample_story.__class__.__step_hooks__

        class PartialHook:
            def __init__(self) -> None:
                self.before_called: int = 0

            def before(self, _: StoryExecutionContext, __: StepExecutionInfo) -> None:
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
