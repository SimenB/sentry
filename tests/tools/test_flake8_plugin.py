from __future__ import annotations

import ast

from tools.flake8_plugin import SentryCheck


def _run(src: str, filename: str = "getsentry/t.py") -> list[str]:
    tree = ast.parse(src)
    errors = sorted(SentryCheck(tree=tree, filename=filename).run())
    return ["t.py:{}:{}: {}".format(*error) for error in errors]


def test_S001() -> None:
    S001_py = """\
class A:
    def called_once():
        pass


A().called_once()
"""

    errors = _run(S001_py)
    assert errors == [
        "t.py:6:0: S001 Avoid using the called_once mock call as it is confusing and "
        "prone to causing invalid test behavior.",
    ]


def test_S002() -> None:
    S002_py = """\
print("print statements are not allowed")
"""

    errors = _run(S002_py)
    assert errors == ["t.py:1:0: S002 print functions or statements are not allowed."]


def test_S003() -> None:
    S003_py = """\
import json
import simplejson
from json import loads, load
from simplejson import JSONDecoder, JSONDecodeError, _default_encoder
import sentry.utils.json as good_json
from sentry.utils.json import JSONDecoder, JSONDecodeError
from .json import Validator


def bad_code():
    a = json.loads("''")
    b = simplejson.loads("''")
    c = loads("''")
    d = load()
"""

    errors = _run(S003_py)
    assert errors == [
        "t.py:1:0: S003 Use `from sentry.utils import json` instead.",
        "t.py:2:0: S003 Use `from sentry.utils import json` instead.",
        "t.py:3:0: S003 Use `from sentry.utils import json` instead.",
        "t.py:4:0: S003 Use `from sentry.utils import json` instead.",
    ]


def test_S004() -> None:
    S004_py = """\
import unittest
from something import func


class Test(unittest.TestCase):
    def test(self) -> None:
        with self.assertRaises(ValueError):
            func()
"""
    errors = _run(S004_py)
    assert errors == [
        "t.py:7:13: S004 Use `pytest.raises` instead for better debuggability.",
    ]


def test_S005() -> None:
    S005_py = """\
from sentry.models import User
"""
    errors = _run(S005_py)
    assert errors == [
        "t.py:1:0: S005 Do not import models from sentry.models but the actual module",
    ]


def test_S006() -> None:
    src = """\
from django.utils.encoding import force_bytes
from django.utils.encoding import force_str
"""
    # only error in tests until we can fix the rest
    assert _run(src, filename="src/sentry/whatever.py") == []
    errors = _run(src, filename="tests/test_foo.py")
    assert errors == [
        "t.py:1:0: S006 Do not use force_bytes / force_str -- test the types directly",
        "t.py:2:0: S006 Do not use force_bytes / force_str -- test the types directly",
    ]


def test_S007() -> None:
    src = """\
from sentry.testutils.outbox import outbox_runner
"""
    # no errors in tests/
    assert _run(src, filename="tests/test_foo.py") == []

    # no errors in src/sentry/testutils/
    assert _run(src, filename="src/sentry/testutils/silo.py") == []

    # errors in other paths
    errors = _run(src, filename="src/sentry/api/endpoints/organization_details.py")
    assert errors == [
        "t.py:1:0: S007 Do not import sentry.testutils into production code.",
    ]

    # Module imports should have errors too.
    src = """\
import sentry.testutils.outbox as outbox_utils
"""
    assert _run(src, filename="tests/test_foo.py") == []

    errors = _run(src, filename="src/sentry/api/endpoints/organization_details.py")
    assert errors == [
        "t.py:1:0: S007 Do not import sentry.testutils into production code.",
    ]


def test_s008() -> None:
    src = """\
from dateutil.parser import parse
"""
    # no errors in source
    assert _run(src, filename="src/sentry/example.py") == []

    # errors in tests
    tests1 = _run(src, filename="tests/test_example.py")
    tests2 = _run(src, filename="src/sentry/testutils/example.py")
    assert (
        tests1
        == tests2
        == ["t.py:1:0: S008 Use datetime.fromisoformat rather than guessing at date formats"]
    )


def test_S009() -> None:
    src = """\
try:
    ...
except OSError:
    raise  # ok: what we want people to do!
except TypeError as e:
    raise RuntimeError()  # ok: reraising a different exception
except ValueError as e:
    raise e  # bad!
"""
    expected = ["t.py:8:4: S009 Use `raise` with no arguments to reraise exceptions"]
    assert _run(src) == expected


def test_S010() -> None:
    src = """\
try:
    ...
except ValueError:
    ... # ok: not a reraise body
except Exception:
    raise  # bad!

try:
    ...
except Exception:
    ...
    raise  # ok: non just a reraise body
"""
    expected = ["t.py:5:0: S010 Except handler does nothing and should be removed"]
    assert _run(src) == expected


def test_S011() -> None:
    src = """\
from sentry.testutils.cases import APITestCase
from django.test import override_settings

def test() -> None:
    with override_settings(SENTRY_OPTIONS={"foo": "bar"}):  # bad
        ...

    with override_settings(
        SENTRY_OPTIONS={"foo": "bar"},  # bad
        OTHER_SETTING=2,  # ok
    ):
        ...

    with override_settings(OTHER_SETTING=2):  # ok
        ...

class Test(ApiTestCase):
    def test(self) -> None:
        with self.settings(SENTRY_OPTIONS={"foo": "bar"}):  # bad
            ...
"""
    expected = [
        "t.py:5:27: S011 Use override_options(...) instead to ensure proper cleanup",
        "t.py:9:8: S011 Use override_options(...) instead to ensure proper cleanup",
        "t.py:19:27: S011 Use override_options(...) instead to ensure proper cleanup",
    ]
    assert _run(src, filename="tests/test_example.py") == expected


def test_S012() -> None:
    src = """\
from rest_framework.permissions import BasePermission, IsAuthenticated, SAFE_METHODS
"""

    expected = [
        "t.py:1:0: S012 Use `from sentry.api.permissions import SentryIsAuthenticated` instead"
    ]
    assert _run(src) == expected


def test_S013() -> None:
    src = """\
from sentry.db.models.fields.array import ArrayField
"""
    expected = ["t.py:1:0: S013 Use `django.contrib.postgres.fields.array.ArrayField` instead"]
    assert _run(src) == expected


def test_S014() -> None:
    src = """\
def test(monkeypatch) -> None: pass
"""
    expected = ["t.py:1:9: S014 Use `unittest.mock` instead"]
    assert _run(src) == expected
