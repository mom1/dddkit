from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from dddkit.exceptions import MissingDependencyError
from dddkit.stories.hooks import StepStatus
from dddkit.stories.story import StepExecutionInfo, StoryExecutionContext

try:
    from prometheus_client import Histogram
except ImportError as e:  # pragma: no cover
    raise MissingDependencyError('prometheus_client', 'prometheus-client', 'prometheus') from e


@dataclass(slots=True)
class PrometheusMetricsHook:
    """A hook that collects and exposes Prometheus metrics for story execution."""

    app_name: str = field(default='dddkit_stories')
    """The name of the service to use in the metrics."""
    prefix: str = 'dddkit_stories'
    """The prefix to use for the metrics."""
    labels: dict[str, str] = field(default_factory=dict)
    """A mapping of labels to add to the metrics.

    The values can be either a string.
    """
    buckets: list[str | float] | None = field(default=None)
    """A list of buckets to use for the histogram."""

    _meta_key: str = 'metrics'
    _metric_name: str = 'executions_latency_ms'
    _step_metric_name: str = 'step_executions_latency_ms'

    _metrics: ClassVar[dict[str, Histogram]] = {}

    def __post_init__(self) -> None:
        self._meta_key = f'{self.prefix}_{self._meta_key}'
        self._metric_name = metric_name = f'{self.prefix}_{self._metric_name}'
        self._step_metric_name = step_metric_name = f'{self.prefix}_{self._step_metric_name}'

        if metric_name not in PrometheusMetricsHook._metrics:
            PrometheusMetricsHook._metrics[metric_name] = Histogram(
                metric_name,
                'Story Execution Time',
                labelnames=['service', 'story_name', 'status', *(self.labels or ())],
                buckets=self.buckets or [10, 25, 50, 100, 300, 500, 1000, 2000, 5000, 10000],
            )
            PrometheusMetricsHook._metrics[step_metric_name] = Histogram(
                step_metric_name,
                'Story step execution time',
                labelnames=['service', 'story_name', 'step_name', 'status', *(self.labels or ())],
                buckets=self.buckets or [10, 25, 50, 100, 300, 500, 1000, 2000, 5000, 10000],
            )

    def after(self, context: StoryExecutionContext, step_info: StepExecutionInfo) -> None:
        status = step_info.meta.get('status') or ''
        story_name = type(context.story).__name__

        PrometheusMetricsHook._metrics[self._step_metric_name].labels(
            service=self.app_name,
            story_name=story_name,
            step_name=step_info.step_name,
            status=status,
            **(self.labels or {}),
        ).observe(int(step_info.meta.get('duration', 0) * 1000))

        if step_info.step_index == len(context.steps) - 1 or status == StepStatus.FAILED:
            PrometheusMetricsHook._metrics[self._metric_name].labels(
                service=self.app_name, story_name=story_name, status=status, **(self.labels or {})
            ).observe(int(sum(step.meta.get('duration', 0) for step in context.steps) * 1000))
