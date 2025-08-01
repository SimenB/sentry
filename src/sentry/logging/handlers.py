from __future__ import annotations

import logging
import random
import re
from typing import Any

from django.utils.timezone import now
from structlog import get_logger
from structlog.processors import _json_fallback_handler

from sentry.utils import json, metrics
from sentry.utils.sdk import get_trace_id

# These are values that come default from logging.LogRecord.
# They are defined here:
# https://github.com/python/cpython/blob/2.7/Lib/logging/__init__.py#L237-L310
throwaways = frozenset(
    (
        "threadName",
        "thread",
        "created",
        "process",
        "processName",
        "args",
        "module",
        "filename",
        "levelno",
        "exc_text",
        "msg",
        "pathname",
        "lineno",
        "funcName",
        "relativeCreated",
        "levelname",
        "msecs",
    )
)


def _json_encoder(*, skipkeys: bool = False) -> json.JSONEncoder:
    return json.JSONEncoder(
        separators=(",", ":"),
        ignore_nan=True,
        skipkeys=skipkeys,
        ensure_ascii=True,
        check_circular=True,
        allow_nan=True,
        indent=None,
        encoding="utf-8",
        default=_json_fallback_handler,
    )


_json_encoder_skipkeys = _json_encoder(skipkeys=True)
_json_encoder_no_skipkeys = _json_encoder(skipkeys=False)


class JSONRenderer:
    def __call__(self, logger, name, event_dict):
        try:
            return _json_encoder_no_skipkeys.encode(event_dict)
        except Exception:
            logging.warning("Failed to serialize event", exc_info=True)
            # in Production, we want to skip non-serializable keys, rather than raise an exception
            if logging.raiseExceptions:
                raise
            else:
                return _json_encoder_skipkeys.encode(event_dict)


class HumanRenderer:
    def __call__(self, logger, name, event_dict):
        level = event_dict.pop("level")
        real_level = level.upper() if isinstance(level, str) else logging.getLevelName(level)
        base = "{} [{}] {}: {}".format(
            now().strftime("%H:%M:%S"),
            real_level,
            event_dict.pop("name", "root"),
            event_dict.pop("event", ""),
        )
        event_dict.pop("sentry.trace.trace_id", None)
        join = " ".join(k + "=" + repr(v) for k, v in event_dict.items())
        return "{}{}".format(base, (" (%s)" % join if join else ""))


class StructLogHandler(logging.StreamHandler):
    def get_log_kwargs(self, record: logging.LogRecord) -> dict[str, Any]:
        kwargs = {k: v for k, v in vars(record).items() if k not in throwaways and v is not None}
        kwargs.update(
            {
                "level": record.levelno,
                "event": record.msg,
                "sentry.trace.trace_id": get_trace_id(),
            }
        )

        if record.args:
            # record.args inside of LogRecord.__init__ gets unrolled
            # if it's the shape `({},)`, a single item dictionary.
            # so we need to check for this, and re-wrap it because
            # down the line of structlog, it's expected to be this
            # original shape.
            if isinstance(record.args, (tuple, list)):
                kwargs["positional_args"] = record.args
            else:
                kwargs["positional_args"] = (record.args,)

        return kwargs

    def emit(self, record: logging.LogRecord, logger: logging.Logger | None = None) -> None:
        # If anyone wants to use the 'extra' kwarg to provide context within
        # structlog, we have to strip all of the default attributes from
        # a record because the RootLogger will take the 'extra' dictionary
        # and just turn them into attributes.
        try:
            if logger is None:
                logger = get_logger()
            logger.log(**self.get_log_kwargs(record=record))
        except Exception:
            if logging.raiseExceptions:
                raise


class GKEStructLogHandler(StructLogHandler):
    def get_log_kwargs(self, record: logging.LogRecord) -> dict[str, Any]:
        kwargs = super().get_log_kwargs(record)

        kwargs.update(
            {
                "logging.googleapis.com/labels": {"name": kwargs.get("name", "root")},
                "severity": record.levelname,
            }
        )
        return kwargs


class MessageContainsFilter(logging.Filter):
    """
    A logging filter that allows log records where the message
    contains given substring(s).

    contains -- a string or list of strings to match
    """

    def __init__(self, contains):
        if not isinstance(contains, list):
            contains = [contains]
        if not all(isinstance(c, str) for c in contains):
            raise TypeError("'contains' must be a string or list of strings")
        self.contains = contains

    def filter(self, record):
        message = record.getMessage()
        return any(c in message for c in self.contains)


whitespace_re = re.compile(r"\s+")
metrics_badchars_re = re.compile("[^a-z0-9_.]")


class MetricsLogHandler(logging.Handler):
    def emit(self, record, logger=None):
        """
        Turn something like:
            > django.request.Forbidden (CSRF cookie not set.): /account
        into:
            > django.request.forbidden_csrf_cookie_not_set
        and track it as an incremented counter.
        """
        key = record.name + "." + record.getMessage()
        key = key.lower()
        key = whitespace_re.sub("_", key)
        key = metrics_badchars_re.sub("", key)
        key = ".".join(key.split(".")[:3])
        metrics.incr(key, skip_internal=False)


class SamplingFilter(logging.Filter):
    """
    A logging filter to sample logs with a fixed probability.

    p      -- probability the log record is emitted. Float in range [0.0, 1.0].
    level  -- sampling applies to log records with this level OR LOWER. Other records always pass through.
    """

    def __init__(self, p: float, level: int | None = None):
        super().__init__()
        assert 0.0 <= p <= 1.0
        self.sample_rate = p
        self.level = logging.INFO if level is None else level

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno <= self.level:
            return random.random() < self.sample_rate
        return True
