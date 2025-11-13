from collections.abc import Callable
from typing import Any
from unittest.mock import Mock

import pytest

from dddkit.stories import I, StepExecutionInfo, Story, StoryExecutionContext
from tests.stories.conftest import AsyncStory, SampleStory, StoryWithError


class TestStoryExecutionContext:
    def test_story_execution_context_str(self, sample_story: SampleStory) -> None:
        context = StoryExecutionContext(story=sample_story)

        context_str = str(context)
        assert context_str.split('\n') == [
            'SampleStory:',
            '    I.step_one',
            '    I.step_two',
            '    I.step_three',
        ]

    def test_story_execution_context_str_custom_template(self, sample_story: SampleStory) -> None:
        for step in (context := StoryExecutionContext(story=sample_story)).steps:
            step.template = '    {meta[status]}{step_index}.{step_name}'

        context_str = str(context)
        assert context_str.split('\n') == [
            'SampleStory:',
            '    0.step_one',
            '    1.step_two',
            '    2.step_three',
        ]


class TestStory:
    def test_story_step_registration(self):
        class TestStory(Story):
            I.step_one
            I.step_two

        story = TestStory()
        assert hasattr(story, 'I')
        assert story.I.__steps__ == ['step_one', 'step_two']

    def test_story_magic_step_registration(self):
        class TestStory(Story):
            I._step_one
            I.step_two

        story = TestStory()
        assert hasattr(story, 'I')
        assert story.I.__steps__ == ['step_two']

    def test_sync_story_execution(self, sample_story: SampleStory) -> None:
        state = sample_story.State()
        sample_story(state)
        assert state == sample_story.State(step_one=True, step_two=True, step_three=True)

    def test_story_with_error(self, story_with_error: StoryWithError) -> None:
        state = story_with_error.State()

        with pytest.raises(ValueError, match='An error occurred'):
            story_with_error(state=state)

        assert state == story_with_error.State(step_one=True)

    async def test_async_story_execution(self, async_story: AsyncStory):
        state = async_story.State()
        await async_story(state)
        assert state == async_story.State(step_one=True, step_two=True)

    def test_story_execution_with_hooks(
        self, sample_story: SampleStory, mock_hook: Callable[[Story], tuple[Mock, Mock, Mock]]
    ) -> None:
        mock_before_hook, mock_after_hook, mock_error_hook = mock_hook(sample_story)

        state = sample_story.State()
        sample_story(state)

        assert mock_before_hook.call_count == 3
        assert mock_after_hook.call_count == 3
        assert mock_error_hook.call_count == 0

        for call in mock_before_hook.call_args_list:
            context, step_info = call[0]
            assert isinstance(context, StoryExecutionContext)
            assert isinstance(step_info, StepExecutionInfo)

    def test_story_with_error_and_hooks(
        self, story_with_error: StoryWithError, mock_hook: Callable[[Story], tuple[Mock, Mock, Mock]]
    ) -> None:
        mock_before_hook, mock_after_hook, mock_error_hook = mock_hook(story_with_error)

        state = story_with_error.State()
        with pytest.raises(ValueError, match='An error occurred'):
            story_with_error(state)

        assert mock_before_hook.call_count == 2
        assert mock_after_hook.call_count == 2
        assert mock_error_hook.call_count == 1

    async def test_async_story_execution_with_hooks(
        self, async_story: AsyncStory, mock_hook: Callable[[Story], tuple[Mock, Mock, Mock]]
    ) -> None:
        mock_before_hook, mock_after_hook, mock_error_hook = mock_hook(async_story)

        state = async_story.State()
        await async_story(state)

        assert mock_before_hook.call_count == 2
        assert mock_after_hook.call_count == 2
        assert mock_error_hook.call_count == 0

        for call in mock_before_hook.call_args_list:
            context, step_info = call[0]
            assert isinstance(context, StoryExecutionContext)
            assert isinstance(step_info, StepExecutionInfo)

    def test_story_error_register_hooks(self) -> None:
        def hook(*args: Any):
            pass

        with pytest.raises(ValueError, match='Unknown hook type: fake'):
            SampleStory.register_hook('fake', hook)  # pyright: ignore[reportArgumentType]
