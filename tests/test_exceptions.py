import pytest

from dddkit.exceptions import MissingDependencyError


def test_missing_dependency_error() -> None:
    exception = MissingDependencyError('prometheus_client', 'prometheus-client', 'prometheus')
    with pytest.raises(MissingDependencyError, match="Package 'prometheus_client'"):
        raise exception
    with pytest.raises(MissingDependencyError, match=r"pip install 'dddkit\[prometheus\]'"):
        raise exception
    with pytest.raises(MissingDependencyError, match='pip install prometheus-client'):
        raise exception
