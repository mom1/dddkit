from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from dddkit.exceptions import MissingDependencyError
from dddkit.stories.hooks import StepStatus
from dddkit.stories.story import StepExecutionInfo, StoryExecutionContext

try:
    from aioprometheus import Histogram  # pyright: ignore[reportPrivateImportUsage]
except ImportError as e:  # pragma: no cover
    raise MissingDependencyError('aioprometheus', extra='aioprometheus') from e


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
    buckets: list[float] | None = field(default=None)
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
                const_labels=(const_labels := {'service': self.app_name, **(self.labels or {})}),
                buckets=self.buckets or [10.0, 25.0, 50.0, 100.0, 300.0, 500.0, 1000.0, 2000.0, 5000.0, 10000.0],
            )
            PrometheusMetricsHook._metrics[step_metric_name] = Histogram(
                step_metric_name,
                'Story step execution time',
                const_labels=const_labels,
                buckets=self.buckets or [10.0, 25.0, 50.0, 100.0, 300.0, 500.0, 1000.0, 2000.0, 5000.0, 10000.0],
            )

    def after(self, context: StoryExecutionContext, step_info: StepExecutionInfo) -> None:
        status = str(step_info.meta.get('status') or '')
        story_name = type(context.story).__name__

        PrometheusMetricsHook._metrics[self._step_metric_name].observe(
            {'story_name': story_name, 'step_name': step_info.step_name, 'status': status},
            int(step_info.meta.get('duration', 0) * 1000),
        )
        if step_info.step_index == len(context.steps) - 1 or status == StepStatus.FAILED:
            PrometheusMetricsHook._metrics[self._metric_name].observe(
                {'story_name': story_name, 'status': status},
                int(sum(step.meta.get('duration', 0) for step in context.steps) * 1000),
            )
