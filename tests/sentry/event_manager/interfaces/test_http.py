import pytest

from sentry import eventstore
from sentry.event_manager import EventManager
from sentry.testutils.pytest.fixtures import django_db_all


@pytest.fixture
def make_http_snapshot(insta_snapshot):
    def inner(data):
        mgr = EventManager(data={"request": data})
        mgr.normalize()
        evt = eventstore.backend.create_event(project_id=1, data=mgr.get_data())

        interface = evt.interfaces.get("request")
        assert interface is not None

        insta_snapshot({"errors": evt.data.get("errors"), "to_json": interface.to_json()})

    return inner


def test_basic(make_http_snapshot) -> None:
    make_http_snapshot(dict(url="http://example.com"))


@django_db_all
def test_full(make_http_snapshot) -> None:
    make_http_snapshot(
        dict(
            api_target="foo",
            method="GET",
            url="http://example.com",
            query_string="foo=bar",
            fragment="foobar",
            headers={"x-foo-bar": "baz"},
            cookies={"foo": "bar"},
            env={"bing": "bong"},
            data="hello world",
        )
    )


def test_query_string_as_dict(make_http_snapshot) -> None:
    make_http_snapshot(dict(url="http://example.com", query_string={"foo": "bar"}))


def test_query_string_as_pairlist(make_http_snapshot) -> None:
    make_http_snapshot(dict(url="http://example.com", query_string=[["foo", "bar"]]))


def test_data_as_dict(make_http_snapshot) -> None:
    make_http_snapshot(dict(url="http://example.com", data={"foo": "bar"}))


@django_db_all
def test_urlencoded_data(make_http_snapshot) -> None:
    make_http_snapshot(
        dict(
            url="http://example.com",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data="foo=bar",
        )
    )


def test_infer_urlencoded_content_type(make_http_snapshot) -> None:
    make_http_snapshot(dict(url="http://example.com", data="foo=bar"))


def test_json_data(make_http_snapshot) -> None:
    make_http_snapshot(
        dict(
            url="http://example.com",
            headers={"Content-Type": "application/json"},
            data='{"foo":"bar"}',
        )
    )


def test_infer_json_content_type(make_http_snapshot) -> None:
    make_http_snapshot(dict(url="http://example.com", data='{"foo":"bar"}'))


@django_db_all
def test_cookies_as_string(make_http_snapshot) -> None:
    make_http_snapshot(dict(url="http://example.com", cookies="a=b;c=d"))
    make_http_snapshot(dict(url="http://example.com", cookies="a=b;c=d"))


def test_cookies_in_header(make_http_snapshot) -> None:
    make_http_snapshot(dict(url="http://example.com", headers={"Cookie": "a=b;c=d"}))


def test_cookies_in_header2(make_http_snapshot) -> None:
    make_http_snapshot(
        dict(url="http://example.com", headers={"Cookie": "a=b;c=d"}, cookies={"foo": "bar"})
    )


def test_query_string_and_fragment_as_params(make_http_snapshot) -> None:
    make_http_snapshot(
        dict(url="http://example.com", query_string="foo\ufffd=bar\u2026", fragment="fragment")
    )


@django_db_all
def test_query_string_and_fragment_in_url(make_http_snapshot) -> None:
    make_http_snapshot(dict(url="http://example.com?foo\ufffd=bar#fragment\u2026"))


def test_header_value_list(make_http_snapshot) -> None:
    make_http_snapshot(dict(url="http://example.com", headers={"Foo": ["1", "2"]}))


def test_header_value_str(make_http_snapshot) -> None:
    make_http_snapshot(dict(url="http://example.com", headers={"Foo": 1}))


def test_invalid_method(make_http_snapshot) -> None:
    make_http_snapshot(dict(url="http://example.com", method="1234"))


@django_db_all
def test_invalid_method2(make_http_snapshot) -> None:
    make_http_snapshot(dict(url="http://example.com", method="A" * 33))


@django_db_all
def test_invalid_method3(make_http_snapshot) -> None:
    make_http_snapshot(dict(url="http://example.com", method="A"))


def test_unknown_method(make_http_snapshot) -> None:
    make_http_snapshot(dict(url="http://example.com", method="TEST"))


def test_unknown_method2(make_http_snapshot) -> None:
    make_http_snapshot(dict(url="http://example.com", method="FOO-BAR"))


def test_unknown_method3(make_http_snapshot) -> None:
    make_http_snapshot(dict(url="http://example.com", method="FOO_BAR"))
