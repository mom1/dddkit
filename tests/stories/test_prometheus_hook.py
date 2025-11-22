from collections.abc import Callable, Generator
from typing import Any
from unittest.mock import ANY

import pytest
from _pytest.fixtures import SubRequest
from prometheus_client import REGISTRY, Histogram
from pytest_mock import MockerFixture

from dddkit.stories import StoryExecutionContext
from dddkit.stories.prometheus import PrometheusMetricsHook
from tests.stories.conftest import SampleStory


class TestPrometheusMetricsHook:
    @pytest.fixture
    def prometheus_hook_factory(self) -> Generator[Callable[..., PrometheusMetricsHook], None, None]:
        def factory(**kwargs: Any) -> PrometheusMetricsHook:
            return PrometheusMetricsHook(**kwargs)

        yield factory
        for collector in PrometheusMetricsHook._metrics.values():  # pyright: ignore[reportPrivateUsage]
            REGISTRY.unregister(collector)
        PrometheusMetricsHook._metrics.clear()  # pyright: ignore[reportPrivateUsage]

    @pytest.fixture(
        params=[
            {'app_name': 'test', 'prefix': 'test_stories'},
            {'app_name': 'test', 'prefix': 'test_stories', 'labels': {'node': 'pod1'}},
        ],
        ids=['name and prefix', 'with labels'],
    )
    def init_data(self, request: SubRequest) -> dict[str, Any]:
        return request.param

    @pytest.fixture
    def prometheus_hook(
        self, prometheus_hook_factory: Callable[..., PrometheusMetricsHook], init_data: dict[str, Any]
    ) -> PrometheusMetricsHook:
        return prometheus_hook_factory(**init_data)

    @pytest.fixture
    def expected_data(self, init_data: dict[str, Any]) -> dict[str, Any]:
        return {
            '_meta_key': f'{init_data.get("prefix")}_metrics',
            '_metric_name': f'{init_data.get("prefix")}_executions_latency_ms',
            '_step_metric_name': f'{init_data.get("prefix")}_step_executions_latency_ms',
            'labels_names': ('service', 'story_name', 'status', *(labels := init_data.get('labels', {}))),
            'labels_names_step': ('service', 'story_name', 'step_name', 'status', *labels),
            'labels': {
                'service': init_data.get('app_name'),
                'story_name': 'SampleStory',
                'status': ANY,
                **labels,
            },
            'labels_step': {
                'service': init_data.get('app_name'),
                'story_name': 'SampleStory',
                'step_name': ANY,
                'status': ANY,
                **labels,
            },
        }

    @pytest.fixture
    def mock_context_story(
        self, sample_story: SampleStory, prometheus_hook: PrometheusMetricsHook, mocker: MockerFixture
    ) -> StoryExecutionContext:
        ctx = StoryExecutionContext(story=sample_story)
        mocker.patch.object(SampleStory, '__context__cls__', autospec=True, return_value=ctx)

        sample_story.register_hook('after', prometheus_hook.after)
        return ctx

    def test_hook_initialization(self, prometheus_hook: PrometheusMetricsHook, expected_data: dict[str, Any]) -> None:
        metric_name = expected_data.get('_metric_name')
        step_metric_name = expected_data.get('_step_metric_name') or ''
        assert prometheus_hook._meta_key == expected_data.get('_meta_key')  # pyright: ignore[reportPrivateUsage]
        assert prometheus_hook._metric_name == metric_name  # pyright: ignore[reportPrivateUsage]

        assert len(PrometheusMetricsHook._metrics) == 2  # pyright: ignore[reportPrivateUsage]
        assert metric_name in PrometheusMetricsHook._metrics  # pyright: ignore[reportPrivateUsage]
        assert isinstance(PrometheusMetricsHook._metrics[metric_name], Histogram)  # pyright: ignore[reportPrivateUsage]

        histogram = PrometheusMetricsHook._metrics[metric_name]  # pyright: ignore[reportPrivateUsage]
        histogram_step = PrometheusMetricsHook._metrics[step_metric_name]  # pyright: ignore[reportPrivateUsage]

        assert histogram._labelnames == expected_data.get('labels_names')  # pyright: ignore[reportPrivateUsage,reportUnknownMemberType]
        assert histogram_step._labelnames == expected_data.get('labels_names_step')  # pyright: ignore[reportPrivateUsage,reportUnknownMemberType]

    def test_hook_initialization_with_same_name(
        self,
        prometheus_hook: PrometheusMetricsHook,
        prometheus_hook_factory: Callable[..., PrometheusMetricsHook],
        init_data: dict[str, Any],
        expected_data: dict[str, Any],
    ):
        hook_second = prometheus_hook_factory(**init_data)
        metric_name = expected_data.get('_metric_name') or ''
        assert len(PrometheusMetricsHook._metrics) == 2  # pyright: ignore[reportPrivateUsage]
        assert hook_second._metrics[metric_name] is prometheus_hook._metrics[metric_name]  # pyright: ignore[reportPrivateUsage]

    def test_hook(
        self,
        sample_story: SampleStory,
        mock_context_story: StoryExecutionContext,
        prometheus_hook: PrometheusMetricsHook,
        expected_data: dict[str, Any],
    ) -> None:
        state = sample_story.State()
        sample_story(state)

        metric_name = expected_data.get('_metric_name') or ''
        step_metric_name = expected_data.get('_step_metric_name') or ''
        expected_meta = (expected_data.get('labels') or {}) | {'story_name': sample_story.__class__.__name__}  # pyright: ignore[reportUnknownVariableType]
        histogram = prometheus_hook._metrics[metric_name]  # pyright: ignore[reportPrivateUsage]
        assert tuple(histogram._metrics) == (tuple(expected_meta.values()),)  # pyright: ignore[reportPrivateUsage,reportUnknownMemberType,reportUnknownArgumentType]

        expected_meta_step = (expected_data.get('labels_step') or {}) | {'story_name': sample_story.__class__.__name__}  # pyright: ignore[reportUnknownVariableType]
        histogram_step = prometheus_hook._metrics[step_metric_name]  # pyright: ignore[reportPrivateUsage]

        assert tuple(histogram_step._metrics) == tuple(  # pyright: ignore[reportPrivateUsage,reportUnknownMemberType,reportUnknownArgumentType]
            (*(expected_meta_step | {'step_name': step.step_name, 'status': step.meta.get('status') or ''}).values(),)  # pyright: ignore[reportUnknownArgumentType]
            for step in mock_context_story.steps
        )
