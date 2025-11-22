class DDDKitError(Exception):
    """Base class for all DDDKit exceptions."""


class MissingDependencyError(DDDKitError, ImportError):  # pyright: ignore[reportUnsafeMultipleInheritance]
    """Missing optional dependency.

    This exception is raised only when a module depends on a dependency that has not been installed.
    """

    def __init__(self, package: str, install_package: str | None = None, extra: str | None = None) -> None:
        super().__init__(
            f'Package {package!r} is not installed but required. You can install it by running '
            f"`pip install 'dddkit[{extra or install_package or package}]'` to install dddkit with the required extra "
            f"or 'pip install {install_package or package}' to install the package separately"
        )
