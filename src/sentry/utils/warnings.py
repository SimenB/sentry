from __future__ import annotations

import warnings
from collections.abc import Iterator
from typing import Protocol


class UnsupportedBackend(RuntimeWarning):
    pass


class DeprecatedSettingWarning(DeprecationWarning):
    def __init__(
        self,
        setting: str,
        replacement: str,
        url: str | None = None,
        removed_in_version: str | None = None,
    ):
        self.setting = setting
        self.replacement = replacement
        self.url = url
        self.removed_in_version = removed_in_version
        super().__init__(setting, replacement, url)

    def __str__(self) -> str:
        chunks = [
            f"The {self.setting} setting is deprecated. Please use {self.replacement} instead."
        ]

        if self.removed_in_version:
            chunks.append(f"This setting will be removed in Sentry {self.removed_in_version}.")

        # TODO(tkaemming): This will be removed from the message in the future
        # when it's added to the API payload separately.
        if self.url:
            chunks.append(f"See {self.url} for more information.")

        return " ".join(chunks)


class _WarningHandler(Protocol):
    def __call__(self, warning: Warning, stacklevel: int | None = None) -> None: ...


class WarningManager:
    """
    Transforms warnings into a standard form and invokes handlers.
    """

    def __init__(
        self, handlers: tuple[_WarningHandler, ...], default_category: type[Warning] = Warning
    ) -> None:
        self.__handlers = handlers
        self.__default_category = default_category

    def warn(
        self,
        message: str | Warning,
        category: type[Warning] | None = None,
        stacklevel: int | None = None,
    ) -> None:
        if isinstance(message, Warning):
            # Maybe log if `category` was passed and isn't a subclass of
            # `type(message)`?
            warning = message
        else:
            if category is None:
                category = self.__default_category

            assert issubclass(category, Warning)
            warning = category(message)

        kwargs = {}
        if stacklevel is not None:
            kwargs["stacklevel"] = stacklevel

        for handler in self.__handlers:
            handler(warning, **kwargs)


class WarningSet:
    """
    Add-only set structure for storing unique warnings.
    """

    def __init__(self) -> None:
        self.__warnings: dict[tuple[object, ...], Warning] = {}

    def __contains__(self, value: object) -> bool:
        assert isinstance(value, Warning)
        return self.__get_key(value) in self.__warnings

    def __len__(self) -> int:
        return len(self.__warnings)

    def __iter__(self) -> Iterator[Warning]:
        yield from self.__warnings.values()

    def __get_key(self, warning: Warning) -> tuple[object, ...]:
        return (type(warning), warning.args if hasattr(warning, "args") else str(warning))

    def add(self, warning: Warning, stacklevel: int | None = None) -> None:
        self.__warnings[self.__get_key(warning)] = warning


# Maintains all unique warnings seen since system startup.
seen_warnings = WarningSet()

manager = WarningManager(
    (
        lambda warning, stacklevel=1: warnings.warn(warning, stacklevel=stacklevel + 2),
        seen_warnings.add,
    )
)

# Make this act like the standard library ``warnings`` module.
warn = manager.warn
