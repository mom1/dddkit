from typing import Any
from unittest.mock import Mock

import pytest

from dddkit.stories import I, StepExecutionInfo, Story, StoryExecutionContext

from .conftest import AsyncStory, SampleStory, StoryWithError

## Tests: Story Structure


def test_when_story_defined_with_steps_then_steps_registered_in_order():
    """Steps declared with I.step_name are registered in declaration order."""

    class OrderProcessingStory(Story):
        I.validate_order
        I.process_payment
        I.fulfill_order

        def validate_order(self, state: Any) -> None:
            pass

        def process_payment(self, state: Any) -> None:
            pass

        def fulfill_order(self, state: Any) -> None:
            pass

    story = OrderProcessingStory()

    assert story.I.__steps__ == ['validate_order', 'process_payment', 'fulfill_order']


def test_when_step_starts_with_underscore_then_not_registered():
    """Private steps (starting with _) are excluded from registration."""

    class StoryWithPrivateSteps(Story):
        I.public_step
        I._private_step

        def public_step(self, state: Any) -> None:
            pass

        def _private_step(self, state: Any) -> None:
            pass

    story = StoryWithPrivateSteps()

    assert story.I.__steps__ == ['public_step']


## Tests: Story Execution


def test_when_story_executed_then_all_steps_run_in_order():
    """Executing story runs all registered steps sequentially."""
    story = SampleStory()
    state = story.State()

    story(state)

    assert state.step_one is True
    assert state.step_two is True
    assert state.step_three is True


async def test_when_async_story_executed_then_all_steps_complete():
    """Async story execution awaits all steps including async ones."""
    story = AsyncStory()
    state = story.State()

    await story(state)

    assert state.step_one is True
    assert state.step_two is True


## Tests: Error Handling


def test_when_step_raises_error_then_execution_stops_and_state_preserved():
    """Error in step halts execution, subsequent steps don't run."""
    story = StoryWithError()
    state = story.State()

    with pytest.raises(ValueError, match='An error occurred'):
        story(state)

    assert state.step_one is True


## Tests: Execution Context


def test_when_context_created_then_shows_story_name_and_steps():
    """StoryExecutionContext string representation shows story structure."""
    story = SampleStory()
    context = StoryExecutionContext(story=story)

    context_str = str(context)

    lines = [line.strip() for line in context_str.split('\n')]
    assert lines[0] == 'SampleStory:'
    assert 'I.step_one' in lines
    assert 'I.step_two' in lines
    assert 'I.step_three' in lines


def test_when_step_template_customized_then_shows_in_context():
    """Custom step template formats context output."""
    story = SampleStory()
    context = StoryExecutionContext(story=story)

    for step in context.steps:
        step.template = '    [{meta[status]}] {step_index}.{step_name}'

    context_str = str(context)

    lines = context_str.split('\n')
    assert lines[0] == 'SampleStory:'
    assert '[pending]' in lines[1] or 'step_one' in lines[1]


def test_given_hooks_registered_when_story_executes_then_hooks_called_for_each_step():
    """Before and after hooks are invoked for every successful step."""
    story = SampleStory()
    before_hook = Mock()
    after_hook = Mock()
    error_hook = Mock()

    story.register_hook('before', before_hook)
    story.register_hook('after', after_hook)
    story.register_hook('error', error_hook)

    state = story.State()

    story(state)

    assert before_hook.call_count == 3
    assert after_hook.call_count == 3
    assert error_hook.call_count == 0

    for call in before_hook.call_args_list:
        context, step_info = call[0]
        assert isinstance(context, StoryExecutionContext)
        assert isinstance(step_info, StepExecutionInfo)


def test_given_error_in_step_when_story_executes_then_error_hook_called():
    """Error hook is invoked when step raises exception."""
    story = StoryWithError()
    before_hook = Mock()
    after_hook = Mock()
    error_hook = Mock()

    story.register_hook('before', before_hook)
    story.register_hook('after', after_hook)
    story.register_hook('error', error_hook)

    state = story.State()

    with pytest.raises(ValueError, match='An error occurred'):
        story(state)

    assert before_hook.call_count == 2
    assert after_hook.call_count == 2
    assert error_hook.call_count == 1


async def test_given_hooks_registered_when_async_story_executes_then_hooks_awaited():
    """Hooks work correctly with async story execution."""
    story = AsyncStory()
    before_hook = Mock()
    after_hook = Mock()
    error_hook = Mock()

    story.register_hook('before', before_hook)
    story.register_hook('after', after_hook)
    story.register_hook('error', error_hook)

    state = story.State()

    await story(state)

    assert before_hook.call_count == 2
    assert after_hook.call_count == 2
    assert error_hook.call_count == 0


## Tests: Invalid Hook Registration


def test_when_invalid_hook_type_registered_then_raises_value_error():
    """Registering hook with unknown type raises ValueError."""
    story = SampleStory()
    fake_hook = lambda *args: None  # pyright: ignore[reportUnknownVariableType,reportUnknownLambdaType]  # noqa: E731

    with pytest.raises(ValueError, match='Unknown hook type: fake'):
        story.register_hook('fake', fake_hook)  # pyright: ignore[reportArgumentType,reportUnknownArgumentType]
