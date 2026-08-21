import pytest


class ListLogger:
    """
    A tiny stand-in for the logger the pipeline passes everywhere.

    Real code calls logger.info / .warning / .error / .exception - this
    just remembers what was said so a test can assert on it if it cares,
    without needing real logging handlers or a _Logs folder on disk.
    """

    def __init__(self):
        self.messages = []

    def _record(self, level, msg, *args, **kwargs):
        self.messages.append((level, msg % args if args else msg))

    def info(self, msg, *args, **kwargs):
        self._record("INFO", msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self._record("WARNING", msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self._record("ERROR", msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        self._record("EXCEPTION", msg, *args, **kwargs)

    def has_warning_containing(self, text: str) -> bool:
        return any(text in msg for level, msg in self.messages if level == "WARNING")


@pytest.fixture
def logger():
    """A fresh fake logger for each test."""
    return ListLogger()