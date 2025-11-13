from collections.abc import Callable, Generator
from dataclasses import dataclass
from types import SimpleNamespace as BaseState
from typing import Any
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

from dddkit.stories import I, Story


@dataclass(frozen=True, slots=True)
class SampleStory(Story):
    """Sample Story."""

    I.step_one
    I.step_two
    I.step_three

    class State(BaseState):
        step_one: bool
        step_two: bool
        step_three: bool

    def step_one(self, state: State) -> None:
        state.step_one = True

    def step_two(self, state: State) -> None:
        state.step_two = True

    def step_three(self, state: State) -> None:
        state.step_three = True


@dataclass(frozen=True, slots=True)
class StoryWithError(Story):
    """Sample Story with error."""

    I.step_one
    I.step_error

    class State(BaseState):
        step_one: bool

    def step_one(self, state: State) -> None:
        state.step_one = True

    def step_error(self, state: State) -> None:
        raise ValueError('An error occurred')


@dataclass(frozen=True, slots=True)
class AsyncStory(Story):
    I.step_one
    I.step_two

    class State(BaseState):
        step_one: bool
        step_two: bool

    async def step_one(self, state: State) -> None:
        state.step_one = True

    def step_two(self, state: State) -> None:
        state.step_two = True


@pytest.fixture
def sample_story() -> Generator[SampleStory, Any, None]:
    yield SampleStory()
    SampleStory.__step_hooks__.clear()


@pytest.fixture
def story_with_error() -> Generator[StoryWithError, Any, None]:
    yield StoryWithError()
    StoryWithError.__step_hooks__.clear()


@pytest.fixture
def async_story() -> Generator[AsyncStory, Any, None]:
    yield AsyncStory()
    AsyncStory.__step_hooks__.clear()


@pytest.fixture
def mock_hook(mocker: MockerFixture) -> Callable[[Story], tuple[Mock, Mock, Mock]]:
    def mock(story: Story) -> tuple[Mock, Mock, Mock]:
        mock_before_hook: Mock = mocker.Mock()
        mock_after_hook: Mock = mocker.Mock()
        mock_error_hook: Mock = mocker.Mock()

        story.register_hook('before', mock_before_hook)
        story.register_hook('after', mock_after_hook)
        story.register_hook('error', mock_error_hook)

        return mock_before_hook, mock_after_hook, mock_error_hook

    return mock
