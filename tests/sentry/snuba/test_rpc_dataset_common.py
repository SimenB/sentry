import pytest

from sentry.search.eap.types import SearchResolverConfig
from sentry.search.events.types import SnubaParams
from sentry.snuba.rpc_dataset_common import RPCBase, TableQuery
from sentry.snuba.spans_rpc import Spans
from sentry.testutils.cases import TestCase


class TestBulkTableQueries(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.snuba_params = SnubaParams()
        self.config = SearchResolverConfig()
        self.resolver = Spans.get_resolver(self.snuba_params, self.config)

    def test_missing_name(self) -> None:
        with pytest.raises(ValueError):
            RPCBase.run_bulk_table_queries(
                [
                    TableQuery("test", ["test"], None, 0, 1, "TestReferrer", None, self.resolver),
                    TableQuery(
                        "test",
                        ["test"],
                        None,
                        0,
                        1,
                        "TestReferrer",
                        None,
                        self.resolver,
                        name="test",
                    ),
                ]
            )

    def test_duplicate_name(self) -> None:
        with pytest.raises(ValueError):
            RPCBase.run_bulk_table_queries(
                [
                    TableQuery(
                        "test",
                        ["test"],
                        None,
                        0,
                        1,
                        "TestReferrer",
                        None,
                        self.resolver,
                        name="test",
                    ),
                    TableQuery(
                        "test1",
                        ["test1"],
                        None,
                        0,
                        1,
                        "TestReferrer",
                        None,
                        self.resolver,
                        name="test",
                    ),
                ]
            )
