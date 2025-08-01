from datetime import timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from django.urls import reverse
from rest_framework.exceptions import ErrorDetail
from sentry_protos.snuba.v1.endpoint_get_traces_pb2 import GetTracesResponse, TraceAttribute
from sentry_protos.snuba.v1.trace_item_attribute_pb2 import AttributeKey, AttributeValue

from sentry.api.endpoints.organization_traces import process_breakdowns
from sentry.snuba.referrer import Referrer
from sentry.testutils.cases import APITestCase, BaseSpansTestCase
from sentry.testutils.helpers import parse_link_header
from sentry.testutils.helpers.datetime import before_now
from sentry.utils.samples import load_data
from sentry.utils.snuba import _snuba_query


class OrganizationTracesEndpointTest(BaseSpansTestCase, APITestCase):
    view = "sentry-api-0-organization-traces"
    is_eap: bool = True

    def setUp(self) -> None:
        super().setUp()
        self.login_as(user=self.user)

    def double_write_segment(
        self,
        *,
        project,
        trace_id,
        transaction_id,
        span_id,
        timestamp,
        duration,
        **kwargs,
    ):
        kwargs.setdefault("measurements", {})
        if "lcp" not in kwargs["measurements"]:
            kwargs["measurements"]["lcp"] = duration
        if "client_sample_rate" not in kwargs["measurements"]:
            kwargs["measurements"]["client_sample_rate"] = 0.1

        # first write to the transactions dataset
        end_timestamp = timestamp + timedelta(microseconds=duration * 1000)
        data = load_data(
            "transaction",
            start_timestamp=timestamp,
            timestamp=end_timestamp,
            trace=trace_id,
            span_id=span_id,
            spans=[],
            event_id=transaction_id,
        )

        for measurement, value in kwargs.get("measurements", {}).items():
            data["measurements"][measurement] = {"value": value}

        if tags := kwargs.get("tags", {}):
            data["tags"] = [[key, val] for key, val in tags.items()]

        if environment := kwargs.pop("environment", None):
            data["environment"] = environment

        self.store_event(
            data=data,
            project_id=project.id,
        )

        self.store_segment(
            project_id=project.id,
            trace_id=trace_id,
            transaction_id=transaction_id,
            span_id=span_id,
            timestamp=timestamp,
            duration=duration,
            organization_id=project.organization.id,
            is_eap=True,
            environment=data.get("environment"),
            **kwargs,
        )

    def create_mock_traces(self):
        project_1 = self.create_project()
        project_2 = self.create_project()

        # Hack: ensure that no span ids with leading 0s are generated for the test
        span_ids = ["1" + uuid4().hex[:15] for _ in range(13)]
        tags = ["", "bar", "bar", "baz", "", "bar", "baz"]
        timestamps = []

        # move this 3 days into the past to ensure less flakey tests
        now = before_now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=3)

        trace_id_1 = uuid4().hex
        timestamps.append(now - timedelta(minutes=10))
        self.double_write_segment(
            project=project_1,
            trace_id=trace_id_1,
            transaction_id=uuid4().hex,
            span_id=span_ids[0],
            timestamp=timestamps[-1],
            transaction="foo",
            duration=60_100,
            exclusive_time=60_100,
            sdk_name="sentry.javascript.node",
        )
        for i in range(1, 4):
            timestamps.append(now - timedelta(minutes=9, seconds=45 - i))
            self.double_write_segment(
                project=project_2,
                trace_id=trace_id_1,
                transaction_id=uuid4().hex,
                span_id=span_ids[i],
                parent_span_id=span_ids[0],
                timestamp=timestamps[-1],
                transaction="bar",
                duration=30_000 + i,
                exclusive_time=30_000 + i,
                tags={"foo": tags[i]},
                sdk_name="sentry.javascript.node",
            )

        trace_id_2 = uuid4().hex
        txn_id_2 = uuid4().hex
        timestamps.append(now - timedelta(days=1, minutes=20))
        self.double_write_segment(
            project=project_1,
            trace_id=trace_id_2,
            transaction_id=txn_id_2,
            span_id=span_ids[4],
            timestamp=timestamps[-1],
            transaction="bar",
            duration=90_123,
            exclusive_time=90_123,
            sdk_name="sentry.javascript.node",
        )
        for i in range(5, 7):
            timestamps.append(now - timedelta(days=1, minutes=19, seconds=55 - i))
            self.double_write_segment(
                project=project_2,
                trace_id=trace_id_2,
                transaction_id=uuid4().hex,
                span_id=span_ids[i],
                parent_span_id=span_ids[4],
                timestamp=timestamps[-1],
                transaction="baz",
                duration=20_000 + i,
                exclusive_time=20_000 + i,
                tags={"foo": tags[i]},
                sdk_name="sentry.javascript.node",
            )

        timestamps.append(now - timedelta(days=1, minutes=19, seconds=59))
        self.store_indexed_span(
            organization_id=project_1.organization.id,
            project_id=project_1.id,
            trace_id=trace_id_2,
            transaction_id=txn_id_2,
            span_id=span_ids[7],
            parent_span_id=span_ids[4],
            timestamp=timestamps[-1],
            transaction="foo",
            duration=1_000,
            exclusive_time=1_000,
            op="http.client",
            is_eap=True,
        )

        timestamps.append(now - timedelta(days=1, minutes=19, seconds=40))
        self.store_indexed_span(
            organization_id=project_1.organization.id,
            project_id=project_1.id,
            trace_id=trace_id_2,
            transaction_id=txn_id_2,
            span_id=span_ids[8],
            parent_span_id=span_ids[4],
            timestamp=timestamps[-1],
            transaction="foo",
            duration=3_000,
            exclusive_time=3_000,
            op="db.sql",
            is_eap=self.is_eap,
        )

        timestamps.append(now - timedelta(days=1, minutes=19, seconds=45))
        self.store_indexed_span(
            organization_id=project_1.organization.id,
            project_id=project_1.id,
            trace_id=trace_id_2,
            transaction_id=txn_id_2,
            span_id=span_ids[9],
            parent_span_id=span_ids[4],
            timestamp=timestamps[-1],
            transaction="foo",
            duration=3,
            exclusive_time=3,
            op="db.sql",
            is_eap=True,
        )

        timestamps.append(now - timedelta(days=2, minutes=30))
        trace_id_3 = uuid4().hex
        self.double_write_segment(
            project=project_1,
            trace_id=trace_id_3,
            transaction_id=uuid4().hex,
            span_id=span_ids[10],
            timestamp=timestamps[-1],
            transaction="qux",
            duration=40_000,
            exclusive_time=40_000,
            tags={"foo": "qux"},
            measurements={
                measurement: 40_000
                for i, measurement in enumerate(
                    [
                        "score.total",
                        "score.inp",
                        "score.weight.inp",
                        "http.response_content_length",
                        "http.decoded_response_content_length",
                        "http.response_transfer_size",
                    ]
                )
            },
            sdk_name="sentry.javascript.remix",
        )

        timestamps.append(now - timedelta(days=2, minutes=29, seconds=50))
        self.double_write_segment(
            project=project_1,
            trace_id=trace_id_3,
            transaction_id=uuid4().hex,
            span_id=span_ids[11],
            parent_span_id=span_ids[10],
            timestamp=timestamps[-1],
            transaction="quz",
            duration=10_000,
            tags={"foo": "quz"},
            sdk_name="sentry.javascript.node",
        )

        error_data = load_data("javascript", timestamp=timestamps[0])
        error_data["contexts"]["trace"] = {
            "type": "trace",
            "trace_id": trace_id_1,
            "span_id": span_ids[0],
        }
        error_data["tags"] = [["transaction", "foo"]]
        self.store_event(error_data, project_id=project_1.id)

        return (
            project_1,
            project_2,
            trace_id_1,
            trace_id_2,
            trace_id_3,
            [int(ts.timestamp() * 1000) for ts in timestamps],
            span_ids,
        )

    def do_request(self, query, features=None, **kwargs):
        if features is None:
            features = [
                "organizations:visibility-explore-view",
                "organizations:global-views",
            ]

        query["dataset"] = "spans"

        with self.feature(features):
            return self.client.get(
                reverse(
                    self.view,
                    kwargs={"organization_id_or_slug": self.organization.slug},
                ),
                query,
                format="json",
                **kwargs,
            )

    def test_no_feature(self) -> None:
        response = self.do_request({}, features=[])
        assert response.status_code == 404, response.data

    def test_no_project(self) -> None:
        response = self.do_request({})
        assert response.status_code == 404, response.data

    def test_bad_params_too_many_per_page(self) -> None:
        query = {
            "project": [self.project.id],
            "field": ["id"],
            "per_page": 1000,
        }

        response = self.do_request(query)
        assert response.status_code == 400, response.data
        assert response.data == {
            "detail": ErrorDetail(
                string="Invalid per_page value. Must be between 1 and 100.",
                code="parse_error",
            ),
        }

    def test_no_traces(self) -> None:
        query = {
            "project": [self.project.id],
            "field": ["id", "parent_span"],
            "maxSpansPerTrace": 1,
        }

        response = self.do_request(query)
        assert response.status_code == 200, response.data
        assert response.data == {
            "data": [],
            "meta": {
                "dataScanned": "full",
                "dataset": "unknown",
                "datasetReason": "unchanged",
                "fields": {},
                "isMetricsData": False,
                "isMetricsExtractedData": False,
                "tips": {},
                "units": {},
            },
        }

    def test_query_not_required(self) -> None:
        query = {
            "project": [self.project.id],
            "field": ["id"],
            "maxSpansPerTrace": 1,
            "query": [""],
        }

        response = self.do_request(query)
        assert response.status_code == 200, response.data

    @patch("sentry_sdk.capture_exception")
    @patch("sentry.api.endpoints.organization_traces.process_breakdowns")
    def test_process_breakdown_error(
        self, mock_process_breakdowns: MagicMock, mock_capture_exception: MagicMock
    ) -> None:
        exception = Exception()

        mock_process_breakdowns.side_effect = exception

        (
            project_1,
            project_2,
            trace_id_1,
            trace_id_2,
            _,
            timestamps,
            span_ids,
        ) = self.create_mock_traces()

        query = {
            "project": [],
            "field": ["id", "parent_span", "span.duration"],
            "query": "foo:[bar, baz]",
            "maxSpansPerTrace": 3,
        }

        response = self.do_request(query)
        assert response.status_code == 200, response.data

        assert response.data["meta"] == {
            "dataScanned": "full",
            "dataset": "unknown",
            "datasetReason": "unchanged",
            "fields": {},
            "isMetricsData": False,
            "isMetricsExtractedData": False,
            "tips": {},
            "units": {},
        }

        result_data = sorted(response.data["data"], key=lambda trace: trace["duration"])

        assert result_data == [
            {
                "trace": trace_id_1,
                "numErrors": 1,
                "numOccurrences": 0,
                "numSpans": 4,
                "matchingSpans": 3,
                "project": project_1.slug,
                "name": "foo",
                "duration": 60_100,
                "start": timestamps[0],
                "end": timestamps[0] + 60_100,
                "rootDuration": 60_100,
                "breakdowns": [],
            },
            {
                "trace": trace_id_2,
                "numErrors": 0,
                "numOccurrences": 0,
                "numSpans": 6,
                "matchingSpans": 2,
                "project": project_1.slug,
                "name": "bar",
                "duration": 90_123,
                "start": timestamps[4],
                "end": timestamps[4] + 90_123,
                "rootDuration": 90_123,
                "breakdowns": [],
            },
        ]

        mock_capture_exception.assert_called_with(
            exception,
            contexts={"bad_traces": {"traces": list(sorted([trace_id_1, trace_id_2]))}},
        )

    def test_use_first_span_for_name(self) -> None:
        trace_id = uuid4().hex
        span_id = "1" + uuid4().hex[:15]
        parent_span_id = "1" + uuid4().hex[:15]
        now = before_now().replace(hour=0, minute=0, second=0, microsecond=0)
        ts = now - timedelta(minutes=10)

        self.double_write_segment(
            project=self.project,
            trace_id=trace_id,
            transaction_id=uuid4().hex,
            span_id=span_id,
            parent_span_id=parent_span_id,
            timestamp=ts,
            transaction="foo",
            duration=60_100,
            exclusive_time=60_100,
            sdk_name="sentry.javascript.node",
            op="bar",
        )

        timestamp = int(ts.timestamp() * 1000)

        query = {
            "project": [],
            "field": ["id", "parent_span", "span.duration"],
            "query": "",
            "maxSpansPerTrace": 3,
        }

        response = self.do_request(query)
        assert response.status_code == 200, response.data

        assert response.data["data"] == [
            {
                "breakdowns": [
                    {
                        "duration": 60_100,
                        "start": timestamp,
                        "end": timestamp + 60_100,
                        "sliceStart": 0,
                        "sliceEnd": 40,
                        "sliceWidth": 40,
                        "isRoot": False,
                        "kind": "project",
                        "project": self.project.slug,
                        "sdkName": "sentry.javascript.node",
                    },
                ],
                "duration": 60_100,
                "end": timestamp + 60_100,
                "name": "foo",
                "numErrors": 0,
                "numOccurrences": 0,
                "numSpans": 1,
                "matchingSpans": 1,
                "project": self.project.slug,
                "start": timestamp,
                "trace": trace_id,
                "rootDuration": 60_100,
            },
        ]

    def test_use_root_span_for_name(self) -> None:
        trace_id = uuid4().hex
        span_id_1 = "1" + uuid4().hex[:15]
        span_id_2 = "1" + uuid4().hex[:15]
        now = before_now().replace(hour=0, minute=0, second=0, microsecond=0)
        ts = now - timedelta(minutes=10)

        self.double_write_segment(
            project=self.project,
            trace_id=trace_id,
            transaction_id=uuid4().hex,
            span_id=span_id_1,
            timestamp=ts,
            transaction="foo",
            duration=60_000,
            exclusive_time=60_000,
            sdk_name="sentry.javascript.remix",
        )

        self.double_write_segment(
            project=self.project,
            trace_id=trace_id,
            transaction_id=uuid4().hex,
            span_id=span_id_2,
            parent_span_id=span_id_1,
            timestamp=ts,
            transaction="foo",
            duration=15_000,
            exclusive_time=15_000,
            sdk_name="sentry.javascript.node",
            op="pageload",
        )

        timestamp = int(ts.timestamp() * 1000)

        query = {
            "project": [],
            "field": ["id", "parent_span", "span.duration"],
            "query": "",
            "maxSpansPerTrace": 3,
        }

        response = self.do_request(query)
        assert response.status_code == 200, response.data

        assert response.data["data"] == [
            {
                "breakdowns": [
                    {
                        "duration": 60_000,
                        "start": timestamp,
                        "end": timestamp + 60_000,
                        "sliceStart": 0,
                        "sliceEnd": 40,
                        "sliceWidth": 40,
                        "isRoot": True,
                        "kind": "project",
                        "project": self.project.slug,
                        "sdkName": "sentry.javascript.remix",
                    },
                    {
                        "duration": 15_000,
                        "start": timestamp,
                        "end": timestamp + 15_000,
                        "sliceStart": 0,
                        "sliceEnd": 10,
                        "sliceWidth": 10,
                        "isRoot": False,
                        "kind": "project",
                        "project": self.project.slug,
                        "sdkName": "sentry.javascript.node",
                    },
                ],
                "duration": 60_000,
                "end": timestamp + 60_000,
                "name": "foo",
                "numErrors": 0,
                "numOccurrences": 0,
                "numSpans": 2,
                "matchingSpans": 2,
                "project": self.project.slug,
                "start": timestamp,
                "trace": trace_id,
                "rootDuration": 60_000,
            },
        ]

    def test_use_pageload_for_name(self) -> None:
        trace_id = uuid4().hex
        span_id = "1" + uuid4().hex[:15]
        parent_span_id = "1" + uuid4().hex[:15]
        now = before_now().replace(hour=0, minute=0, second=0, microsecond=0)
        ts = now - timedelta(minutes=10)

        self.double_write_segment(
            project=self.project,
            trace_id=trace_id,
            transaction_id=uuid4().hex,
            span_id=span_id,
            parent_span_id=parent_span_id,
            timestamp=ts,
            transaction="foo",
            duration=60_100,
            exclusive_time=60_100,
            sdk_name="sentry.javascript.node",
            op="pageload",
        )

        timestamp = int(ts.timestamp() * 1000)

        query = {
            "project": [],
            "field": ["id", "parent_span", "span.duration"],
            "query": "",
            "maxSpansPerTrace": 3,
        }

        response = self.do_request(query)
        assert response.status_code == 200, response.data

        assert response.data["data"] == [
            {
                "breakdowns": [
                    {
                        "duration": 60_100,
                        "start": timestamp,
                        "end": timestamp + 60_100,
                        "sliceStart": 0,
                        "sliceEnd": 40,
                        "sliceWidth": 40,
                        "isRoot": False,
                        "kind": "project",
                        "project": self.project.slug,
                        "sdkName": "sentry.javascript.node",
                    },
                ],
                "duration": 60_100,
                "end": timestamp + 60_100,
                "name": "foo",
                "numErrors": 0,
                "numOccurrences": 0,
                "numSpans": 1,
                "matchingSpans": 1,
                "project": self.project.slug,
                "start": timestamp,
                "trace": trace_id,
                "rootDuration": 60_100,
            },
        ]

    def test_use_separate_referrers(self) -> None:
        now = before_now().replace(hour=0, minute=0, second=0, microsecond=0)
        start = now - timedelta(days=2)
        end = now - timedelta(days=1)
        trace_id = uuid4().hex

        with (
            patch(
                "sentry.api.endpoints.organization_traces.get_traces_rpc",
                return_value=GetTracesResponse(
                    traces=[
                        GetTracesResponse.Trace(
                            attributes=[
                                TraceAttribute(
                                    key=TraceAttribute.Key.KEY_TRACE_ID,
                                    value=AttributeValue(val_str=trace_id),
                                    type=AttributeKey.Type.TYPE_STRING,
                                ),
                                TraceAttribute(
                                    key=TraceAttribute.Key.KEY_START_TIMESTAMP,
                                    value=AttributeValue(val_double=start.timestamp()),
                                    type=AttributeKey.Type.TYPE_DOUBLE,
                                ),
                                TraceAttribute(
                                    key=TraceAttribute.Key.KEY_END_TIMESTAMP,
                                    value=AttributeValue(val_double=end.timestamp()),
                                    type=AttributeKey.Type.TYPE_DOUBLE,
                                ),
                            ],
                        )
                    ],
                ),
            ),
            patch("sentry.utils.snuba._snuba_query", wraps=_snuba_query) as mock_snuba_query,
        ):
            query = {
                "project": [self.project.id],
                "field": ["id", "parent_span", "span.duration"],
            }

            response = self.do_request(query)
            assert response.status_code == 200, response.data

            actual_referrers = {
                call[0][0][2].headers["referer"] for call in mock_snuba_query.call_args_list
            }

        assert {
            Referrer.API_TRACE_EXPLORER_TRACES_ERRORS.value,
            Referrer.API_TRACE_EXPLORER_TRACES_OCCURRENCES.value,
        } == actual_referrers

    def test_matching_tag(self) -> None:
        (
            project_1,
            project_2,
            trace_id_1,
            trace_id_2,
            _,
            timestamps,
            span_ids,
        ) = self.create_mock_traces()

        q = ["foo:[bar, baz]"]

        for features in [
            None,  # use the default features
            ["organizations:visibility-explore-view"],
        ]:
            query = {
                # only query for project_2 but expect traces to start from project_1
                "project": [project_2.id],
                "field": ["id", "parent_span", "span.duration"],
                "query": q,
                "maxSpansPerTrace": 4,
            }

            response = self.do_request(query, features=features)
            assert response.status_code == 200, response.data

            assert response.data["meta"] == {
                "dataScanned": "full",
                "dataset": "unknown",
                "datasetReason": "unchanged",
                "fields": {},
                "isMetricsData": False,
                "isMetricsExtractedData": False,
                "tips": {},
                "units": {},
            }

            result_data = sorted(response.data["data"], key=lambda trace: trace["duration"])

            assert result_data == [
                {
                    "trace": trace_id_1,
                    "numErrors": 1,
                    "numOccurrences": 0,
                    "numSpans": 4,
                    "matchingSpans": 3,
                    "project": project_1.slug,
                    "name": "foo",
                    "duration": 60_100,
                    "start": timestamps[0],
                    "end": timestamps[0] + 60_100,
                    "rootDuration": 60_100,
                    "breakdowns": [
                        {
                            "project": project_1.slug,
                            "sdkName": "sentry.javascript.node",
                            "isRoot": True,
                            "start": timestamps[0],
                            "end": timestamps[0] + 60_100,
                            "sliceStart": 0,
                            "sliceEnd": 40,
                            "sliceWidth": 40,
                            "kind": "project",
                            "duration": 60_100,
                        },
                        {
                            "project": project_2.slug,
                            "sdkName": "sentry.javascript.node",
                            "isRoot": False,
                            "start": timestamps[1] + 522,
                            "end": timestamps[3] + 30_003 + 61,
                            "sliceStart": 11,
                            "sliceEnd": 32,
                            "sliceWidth": 21,
                            "kind": "project",
                            "duration": timestamps[3] - timestamps[1] + 30_003,
                        },
                    ],
                },
                {
                    "trace": trace_id_2,
                    "numErrors": 0,
                    "numOccurrences": 0,
                    "numSpans": 6,
                    "matchingSpans": 2,
                    "project": project_1.slug,
                    "name": "bar",
                    "duration": 90_123,
                    "start": timestamps[4],
                    "end": timestamps[4] + 90_123,
                    "rootDuration": 90_123,
                    "breakdowns": [
                        {
                            "project": project_1.slug,
                            "sdkName": "sentry.javascript.node",
                            "isRoot": True,
                            "start": timestamps[4],
                            "end": timestamps[4] + 90_123,
                            "sliceStart": 0,
                            "sliceEnd": 40,
                            "sliceWidth": 40,
                            "kind": "project",
                            "duration": 90_123,
                        },
                        {
                            "project": project_2.slug,
                            "sdkName": "sentry.javascript.node",
                            "isRoot": False,
                            "start": timestamps[5] - 988,
                            "end": timestamps[6] + 20_006 + 536,
                            "sliceStart": 4,
                            "sliceEnd": 14,
                            "sliceWidth": 10,
                            "kind": "project",
                            "duration": timestamps[6] - timestamps[5] + 20_006,
                        },
                    ],
                },
            ]

    def test_environment_filter(self) -> None:
        trace_id = uuid4().hex
        span_id = "1" + uuid4().hex[:15]
        timestamp = before_now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(
            days=3
        )

        self.double_write_segment(
            project=self.project,
            trace_id=trace_id,
            transaction_id=uuid4().hex,
            span_id=span_id,
            timestamp=timestamp,
            transaction="foo",
            duration=60_100,
            exclusive_time=60_100,
            sdk_name="sentry.javascript.node",
            environment="prod",
        )

        self.double_write_segment(
            project=self.project,
            trace_id=uuid4().hex,
            transaction_id=uuid4().hex,
            span_id=uuid4().hex[:16],
            timestamp=timestamp,
            transaction="bar",
            duration=60_100,
            exclusive_time=60_100,
            sdk_name="sentry.javascript.node",
            environment="test",
        )

        query = {
            # only query for project_2 but expect traces to start from project_1
            "project": [self.project.id],
            "field": ["id", "parent_span", "span.duration"],
            "environment": "prod",
        }

        ts = timestamp.timestamp() * 1000

        response = self.do_request(query)
        assert response.status_code == 200, response.data
        assert response.data["data"] == [
            {
                "breakdowns": [
                    {
                        "duration": 60_100,
                        "start": ts,
                        "end": ts + 60_100,
                        "isRoot": True,
                        "kind": "project",
                        "project": self.project.slug,
                        "sdkName": "sentry.javascript.node",
                        "sliceEnd": 40,
                        "sliceStart": 0,
                        "sliceWidth": 40,
                    },
                ],
                "duration": 60_100,
                "start": ts,
                "end": ts + 60_100,
                "matchingSpans": 1,
                "name": "foo",
                "numErrors": 0,
                "numOccurrences": 0,
                "numSpans": 1,
                "project": self.project.slug,
                "rootDuration": 60_100,
                "trace": trace_id,
            },
        ]

    def test_invalid_sort(self) -> None:
        for sort in ["foo", "-foo"]:
            query = {
                "project": [self.project.id],
                "field": ["id", "parent_span"],
                "sort": sort,
            }

            response = self.do_request(query)
            assert response.status_code == 400, response.data
            assert response.data == {
                "detail": ErrorDetail(string=f"Unsupported sort: {sort}", code="parse_error"),
            }

    def test_sort_by_timestamp(self) -> None:
        (
            project_1,
            project_2,
            trace_id_1,
            trace_id_2,
            _,
            timestamps,
            span_ids,
        ) = self.create_mock_traces()

        expected = [
            {
                "trace": trace_id_1,
                "numErrors": 1,
                "numOccurrences": 0,
                "numSpans": 4,
                "matchingSpans": 3,
                "project": project_1.slug,
                "name": "foo",
                "duration": 60_100,
                "start": timestamps[0],
                "end": timestamps[0] + 60_100,
                "rootDuration": 60_100,
                "breakdowns": [
                    {
                        "project": project_1.slug,
                        "sdkName": "sentry.javascript.node",
                        "isRoot": True,
                        "start": timestamps[0],
                        "end": timestamps[0] + 60_100,
                        "sliceStart": 0,
                        "sliceEnd": 40,
                        "sliceWidth": 40,
                        "kind": "project",
                        "duration": 60_100,
                    },
                    {
                        "project": project_2.slug,
                        "sdkName": "sentry.javascript.node",
                        "isRoot": False,
                        "start": timestamps[1] + 522,
                        "end": timestamps[3] + 30_003 + 61,
                        "sliceStart": 11,
                        "sliceEnd": 32,
                        "sliceWidth": 21,
                        "kind": "project",
                        "duration": timestamps[3] - timestamps[1] + 30_003,
                    },
                ],
            },
            {
                "trace": trace_id_2,
                "numErrors": 0,
                "numOccurrences": 0,
                "numSpans": 6,
                "matchingSpans": 2,
                "project": project_1.slug,
                "name": "bar",
                "duration": 90_123,
                "start": timestamps[4],
                "end": timestamps[4] + 90_123,
                "rootDuration": 90_123,
                "breakdowns": [
                    {
                        "project": project_1.slug,
                        "sdkName": "sentry.javascript.node",
                        "isRoot": True,
                        "start": timestamps[4],
                        "end": timestamps[4] + 90_123,
                        "sliceStart": 0,
                        "sliceEnd": 40,
                        "sliceWidth": 40,
                        "kind": "project",
                        "duration": 90_123,
                    },
                    {
                        "project": project_2.slug,
                        "sdkName": "sentry.javascript.node",
                        "isRoot": False,
                        "start": timestamps[5] - 988,
                        "end": timestamps[6] + 20_006 + 536,
                        "sliceStart": 4,
                        "sliceEnd": 14,
                        "sliceWidth": 10,
                        "kind": "project",
                        "duration": timestamps[6] - timestamps[5] + 20_006,
                    },
                ],
            },
        ]

        descending = True

        q = ["foo:[bar, baz]"]

        expected = sorted(
            expected,
            key=lambda trace: trace["start"],
            reverse=descending,
        )

        query = {
            # only query for project_2 but expect traces to start from project_1
            "project": [str(project_2.id)],
            "field": ["id", "parent_span", "span.duration"],
            "query": q,
            "sort": "-timestamp" if descending else "timestamp",
            "per_page": "1",
        }
        response = self.do_request(query)
        assert response.status_code == 200, response.data
        assert response.data["data"] == [expected[0]]

        links = parse_link_header(response.headers["Link"])
        prev_link = next(link for link in links.values() if link["rel"] == "previous")
        assert prev_link["results"] == "false"
        next_link = next(link for link in links.values() if link["rel"] == "next")
        assert next_link["results"] == "true"
        assert next_link["cursor"]

        query = {
            # only query for project_2 but expect traces to start from project_1
            "project": [str(project_2.id)],
            "field": ["id", "parent_span", "span.duration"],
            "query": q,
            "sort": "-timestamp" if descending else "timestamp",
            "per_page": "1",
            "cursor": next_link["cursor"],
        }
        response = self.do_request(query)
        assert response.status_code == 200, response.data
        assert response.data["data"] == [expected[1]]

        links = parse_link_header(response.headers["Link"])
        prev_link = next(link for link in links.values() if link["rel"] == "previous")
        assert prev_link["results"] == "true"
        next_link = next(link for link in links.values() if link["rel"] == "next")
        assert next_link["results"] == "false"


@pytest.mark.parametrize(
    ["data", "traces_range", "expected"],
    [
        pytest.param(
            [
                {
                    "trace": "a" * 32,
                    "project": "foo",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "foo1",
                    "precise.start_ts": 0,
                    "precise.finish_ts": 0.1,
                },
            ],
            {"a" * 32: (0, 100, 10)},
            {
                "a"
                * 32: [
                    {
                        "project": "foo",
                        "sdkName": "sentry.javascript.node",
                        "start": 0,
                        "end": 100,
                        "sliceStart": 0,
                        "sliceEnd": 10,
                        "sliceWidth": 10,
                        "kind": "project",
                        "duration": 100,
                        "isRoot": False,
                    },
                ],
            },
            id="single transaction",
        ),
        pytest.param(
            [
                {
                    "trace": "a" * 32,
                    "project": "foo",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "foo1",
                    "precise.start_ts": 0,
                    "precise.finish_ts": 0.1,
                },
                {
                    "trace": "a" * 32,
                    "project": "bar",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "bar1",
                    "precise.start_ts": 0.025,
                    "precise.finish_ts": 0.075,
                },
            ],
            {"a" * 32: (0, 100, 20)},
            {
                "a"
                * 32: [
                    {
                        "project": "foo",
                        "sdkName": "sentry.javascript.node",
                        "start": 0,
                        "end": 100,
                        "sliceStart": 0,
                        "sliceEnd": 20,
                        "sliceWidth": 20,
                        "kind": "project",
                        "duration": 100,
                        "isRoot": False,
                    },
                    {
                        "project": "bar",
                        "sdkName": "sentry.javascript.node",
                        "start": 25,
                        "end": 75,
                        "sliceStart": 5,
                        "sliceEnd": 15,
                        "sliceWidth": 10,
                        "kind": "project",
                        "duration": 50,
                        "isRoot": False,
                    },
                ],
            },
            id="two transactions different project nested",
        ),
        pytest.param(
            [
                {
                    "trace": "a" * 32,
                    "project": "foo",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "foo1",
                    "precise.start_ts": 0,
                    "precise.finish_ts": 0.05,
                },
                {
                    "trace": "a" * 32,
                    "project": "bar",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "bar1",
                    "precise.start_ts": 0.025,
                    "precise.finish_ts": 0.075,
                },
                {
                    "trace": "a" * 32,
                    "project": "baz",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "baz1",
                    "precise.start_ts": 0.05,
                    "precise.finish_ts": 0.1,
                },
            ],
            {"a" * 32: (0, 100, 20)},
            {
                "a"
                * 32: [
                    {
                        "project": "foo",
                        "sdkName": "sentry.javascript.node",
                        "start": 0,
                        "end": 50,
                        "sliceStart": 0,
                        "sliceEnd": 10,
                        "sliceWidth": 10,
                        "kind": "project",
                        "duration": 50,
                        "isRoot": False,
                    },
                    {
                        "project": "bar",
                        "sdkName": "sentry.javascript.node",
                        "start": 25,
                        "end": 75,
                        "sliceStart": 5,
                        "sliceEnd": 15,
                        "sliceWidth": 10,
                        "kind": "project",
                        "duration": 50,
                        "isRoot": False,
                    },
                    {
                        "project": "baz",
                        "sdkName": "sentry.javascript.node",
                        "start": 50,
                        "end": 100,
                        "sliceStart": 10,
                        "sliceEnd": 20,
                        "sliceWidth": 10,
                        "kind": "project",
                        "duration": 50,
                        "isRoot": False,
                    },
                ],
            },
            id="three transactions different project overlapping",
        ),
        pytest.param(
            [
                {
                    "trace": "a" * 32,
                    "project": "foo",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "foo1",
                    "precise.start_ts": 0,
                    "precise.finish_ts": 0.025,
                },
                {
                    "trace": "a" * 32,
                    "project": "bar",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "bar1",
                    "precise.start_ts": 0.05,
                    "precise.finish_ts": 0.075,
                },
            ],
            {"a" * 32: (0, 75, 15)},
            {
                "a"
                * 32: [
                    {
                        "project": "foo",
                        "sdkName": "sentry.javascript.node",
                        "start": 0,
                        "end": 25,
                        "sliceStart": 0,
                        "sliceEnd": 5,
                        "sliceWidth": 5,
                        "kind": "project",
                        "duration": 25,
                        "isRoot": False,
                    },
                    {
                        "project": "bar",
                        "sdkName": "sentry.javascript.node",
                        "start": 50,
                        "end": 75,
                        "sliceStart": 10,
                        "sliceEnd": 15,
                        "sliceWidth": 5,
                        "kind": "project",
                        "duration": 25,
                        "isRoot": False,
                    },
                ],
            },
            id="two transactions different project non overlapping",
        ),
        pytest.param(
            [
                {
                    "trace": "a" * 32,
                    "project": "foo",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "foo1",
                    "precise.start_ts": 0,
                    "precise.finish_ts": 0.1,
                },
                {
                    "trace": "a" * 32,
                    "project": "foo",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "foo2",
                    "precise.start_ts": 0.025,
                    "precise.finish_ts": 0.075,
                },
            ],
            {"a" * 32: (0, 100, 10)},
            {
                "a"
                * 32: [
                    {
                        "project": "foo",
                        "sdkName": "sentry.javascript.node",
                        "start": 0,
                        "end": 100,
                        "sliceStart": 0,
                        "sliceEnd": 10,
                        "sliceWidth": 10,
                        "kind": "project",
                        "duration": 100,
                        "isRoot": False,
                    },
                ],
            },
            id="two transactions same project nested",
        ),
        pytest.param(
            [
                {
                    "trace": "a" * 32,
                    "project": "foo",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "foo1",
                    "precise.start_ts": 0,
                    "precise.finish_ts": 0.075,
                },
                {
                    "trace": "a" * 32,
                    "project": "foo",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "foo2",
                    "precise.start_ts": 0.025,
                    "precise.finish_ts": 0.1,
                },
            ],
            {"a" * 32: (0, 100, 10)},
            {
                "a"
                * 32: [
                    {
                        "project": "foo",
                        "sdkName": "sentry.javascript.node",
                        "start": 0,
                        "end": 100,
                        "sliceStart": 0,
                        "sliceEnd": 10,
                        "sliceWidth": 10,
                        "kind": "project",
                        "duration": 100,
                        "isRoot": False,
                    },
                ],
            },
            id="two transactions same project overlapping",
        ),
        pytest.param(
            [
                {
                    "trace": "a" * 32,
                    "project": "foo",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "foo1",
                    "precise.start_ts": 0,
                    "precise.finish_ts": 0.025,
                },
                {
                    "trace": "a" * 32,
                    "project": "foo",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "foo2",
                    "precise.start_ts": 0.05,
                    "precise.finish_ts": 0.075,
                },
            ],
            {"a" * 32: (0, 75, 15)},
            {
                "a"
                * 32: [
                    {
                        "project": "foo",
                        "sdkName": "sentry.javascript.node",
                        "start": 0,
                        "end": 25,
                        "sliceStart": 0,
                        "sliceEnd": 5,
                        "sliceWidth": 5,
                        "kind": "project",
                        "duration": 25,
                        "isRoot": False,
                    },
                    {
                        "project": "foo",
                        "sdkName": "sentry.javascript.node",
                        "start": 50,
                        "end": 75,
                        "sliceStart": 10,
                        "sliceEnd": 15,
                        "sliceWidth": 5,
                        "kind": "project",
                        "duration": 25,
                        "isRoot": False,
                    },
                ],
            },
            id="two transactions same project non overlapping",
        ),
        pytest.param(
            [
                {
                    "trace": "a" * 32,
                    "project": "foo",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "foo1",
                    "precise.start_ts": 0,
                    "precise.finish_ts": 0.1,
                },
                {
                    "trace": "a" * 32,
                    "project": "bar",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "bar1",
                    "precise.start_ts": 0.02,
                    "precise.finish_ts": 0.08,
                },
                {
                    "trace": "a" * 32,
                    "project": "baz",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "baz1",
                    "precise.start_ts": 0.04,
                    "precise.finish_ts": 0.06,
                },
            ],
            {"a" * 32: (0, 100, 10)},
            {
                "a"
                * 32: [
                    {
                        "project": "foo",
                        "sdkName": "sentry.javascript.node",
                        "start": 0,
                        "end": 100,
                        "sliceStart": 0,
                        "sliceEnd": 10,
                        "sliceWidth": 10,
                        "kind": "project",
                        "duration": 100,
                        "isRoot": False,
                    },
                    {
                        "project": "bar",
                        "sdkName": "sentry.javascript.node",
                        "start": 20,
                        "end": 80,
                        "sliceStart": 2,
                        "sliceEnd": 8,
                        "sliceWidth": 6,
                        "kind": "project",
                        "duration": 60,
                        "isRoot": False,
                    },
                    {
                        "project": "baz",
                        "sdkName": "sentry.javascript.node",
                        "start": 40,
                        "end": 60,
                        "sliceStart": 4,
                        "sliceEnd": 6,
                        "sliceWidth": 2,
                        "kind": "project",
                        "duration": 20,
                        "isRoot": False,
                    },
                ],
            },
            id="three transactions different project nested",
        ),
        pytest.param(
            [
                {
                    "trace": "a" * 32,
                    "project": "foo",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "foo1",
                    "precise.start_ts": 0,
                    "precise.finish_ts": 0.1,
                },
                {
                    "trace": "a" * 32,
                    "project": "bar",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "bar1",
                    "precise.start_ts": 0.025,
                    "precise.finish_ts": 0.05,
                },
                {
                    "trace": "a" * 32,
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "project": "baz",
                    "transaction": "baz1",
                    "precise.start_ts": 0.05,
                    "precise.finish_ts": 0.075,
                },
            ],
            {"a" * 32: (0, 100, 20)},
            {
                "a"
                * 32: [
                    {
                        "project": "foo",
                        "sdkName": "sentry.javascript.node",
                        "start": 0,
                        "end": 100,
                        "sliceStart": 0,
                        "sliceEnd": 20,
                        "sliceWidth": 20,
                        "kind": "project",
                        "duration": 100,
                        "isRoot": False,
                    },
                    {
                        "project": "bar",
                        "sdkName": "sentry.javascript.node",
                        "start": 25,
                        "end": 50,
                        "sliceStart": 5,
                        "sliceEnd": 10,
                        "sliceWidth": 5,
                        "kind": "project",
                        "duration": 25,
                        "isRoot": False,
                    },
                    {
                        "project": "baz",
                        "sdkName": "sentry.javascript.node",
                        "start": 50,
                        "end": 75,
                        "sliceStart": 10,
                        "sliceEnd": 15,
                        "sliceWidth": 5,
                        "kind": "project",
                        "duration": 25,
                        "isRoot": False,
                    },
                ],
            },
            id="three transactions different project 2 overlap the first",
        ),
        pytest.param(
            [
                {
                    "trace": "a" * 32,
                    "project": "foo",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "foo1",
                    "precise.start_ts": 0,
                    "precise.finish_ts": 0.05,
                },
                {
                    "trace": "a" * 32,
                    "project": "bar",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "bar1",
                    "precise.start_ts": 0.02,
                    "precise.finish_ts": 0.03,
                },
                {
                    "trace": "a" * 32,
                    "project": "baz",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "baz1",
                    "precise.start_ts": 0.05,
                    "precise.finish_ts": 0.075,
                },
            ],
            {"a" * 32: (0, 75, 15)},
            {
                "a"
                * 32: [
                    {
                        "project": "foo",
                        "sdkName": "sentry.javascript.node",
                        "start": 0,
                        "end": 50,
                        "sliceStart": 0,
                        "sliceEnd": 10,
                        "sliceWidth": 10,
                        "kind": "project",
                        "duration": 50,
                        "isRoot": False,
                    },
                    {
                        "project": "bar",
                        "sdkName": "sentry.javascript.node",
                        "start": 20,
                        "end": 30,
                        "sliceStart": 4,
                        "sliceEnd": 6,
                        "sliceWidth": 2,
                        "kind": "project",
                        "duration": 10,
                        "isRoot": False,
                    },
                    {
                        "project": "baz",
                        "sdkName": "sentry.javascript.node",
                        "start": 50,
                        "end": 75,
                        "sliceStart": 10,
                        "sliceEnd": 15,
                        "sliceWidth": 5,
                        "kind": "project",
                        "duration": 25,
                        "isRoot": False,
                    },
                ],
            },
            id="three transactions different project 1 overlap the first and other non overlap",
        ),
        pytest.param(
            [
                {
                    "trace": "a" * 32,
                    "project": "foo",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "foo1",
                    "precise.start_ts": 0,
                    "precise.finish_ts": 0.05,
                },
                {
                    "trace": "a" * 32,
                    "project": "bar",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "bar1",
                    "precise.start_ts": 0.02,
                    "precise.finish_ts": 0.03,
                },
                {
                    "trace": "a" * 32,
                    "project": "baz",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "baz1",
                    "precise.start_ts": 0.04,
                    "precise.finish_ts": 0.06,
                },
            ],
            {"a" * 32: (0, 60, 6)},
            {
                "a"
                * 32: [
                    {
                        "project": "foo",
                        "sdkName": "sentry.javascript.node",
                        "start": 0,
                        "end": 50,
                        "sliceStart": 0,
                        "sliceEnd": 5,
                        "sliceWidth": 5,
                        "kind": "project",
                        "duration": 50,
                        "isRoot": False,
                    },
                    {
                        "project": "bar",
                        "sdkName": "sentry.javascript.node",
                        "start": 20,
                        "end": 30,
                        "sliceStart": 2,
                        "sliceEnd": 3,
                        "sliceWidth": 1,
                        "kind": "project",
                        "duration": 10,
                        "isRoot": False,
                    },
                    {
                        "project": "baz",
                        "sdkName": "sentry.javascript.node",
                        "start": 40,
                        "end": 60,
                        "sliceStart": 4,
                        "sliceEnd": 6,
                        "sliceWidth": 2,
                        "kind": "project",
                        "duration": 20,
                        "isRoot": False,
                    },
                ],
            },
            id="three transactions different project 2 overlap and second extend past parent",
        ),
        pytest.param(
            [
                {
                    "trace": "a" * 32,
                    "project": "foo",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "foo1",
                    "precise.start_ts": 0,
                    "precise.finish_ts": 0.05,
                },
                {
                    "trace": "a" * 32,
                    "project": "bar",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "bar1",
                    "precise.start_ts": 0.01,
                    "precise.finish_ts": 0.02,
                },
                {
                    "trace": "a" * 32,
                    "project": "foo",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "foo1",
                    "precise.start_ts": 0.03,
                    "precise.finish_ts": 0.04,
                },
            ],
            {"a" * 32: (0, 50, 10)},
            {
                "a"
                * 32: [
                    {
                        "project": "foo",
                        "sdkName": "sentry.javascript.node",
                        "start": 0,
                        "end": 50,
                        "sliceStart": 0,
                        "sliceEnd": 10,
                        "sliceWidth": 10,
                        "kind": "project",
                        "duration": 50,
                        "isRoot": False,
                    },
                    {
                        "project": "bar",
                        "sdkName": "sentry.javascript.node",
                        "start": 10,
                        "end": 20,
                        "sliceStart": 2,
                        "sliceEnd": 4,
                        "sliceWidth": 2,
                        "kind": "project",
                        "duration": 10,
                        "isRoot": False,
                    },
                ],
            },
            id="three transactions same project with another project between",
        ),
        pytest.param(
            [
                {
                    "trace": "a" * 32,
                    "project": "foo",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "foo1",
                    "precise.start_ts": 0,
                    "precise.finish_ts": 0.1,
                },
            ],
            {"a" * 32: (0, 50, 5)},
            {
                "a"
                * 32: [
                    {
                        "project": "foo",
                        "sdkName": "sentry.javascript.node",
                        "start": 0,
                        "end": 50,
                        "sliceStart": 0,
                        "sliceEnd": 5,
                        "sliceWidth": 5,
                        "kind": "project",
                        "duration": 50,
                        "isRoot": False,
                    },
                ],
            },
            id="clips intervals to be within trace",
        ),
        pytest.param(
            [
                {
                    "trace": "a" * 32,
                    "project": "foo",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "foo1",
                    "precise.start_ts": 0,
                    "precise.finish_ts": 0.05,
                },
            ],
            {"a" * 32: (0, 100, 5)},
            {
                "a"
                * 32: [
                    {
                        "project": "foo",
                        "sdkName": "sentry.javascript.node",
                        "start": 0,
                        "end": 40,
                        "sliceStart": 0,
                        "sliceEnd": 2,
                        "sliceWidth": 2,
                        "kind": "project",
                        "duration": 50,
                        "isRoot": False,
                    },
                ],
            },
            id="adds other interval at end",
        ),
        pytest.param(
            [
                {
                    "trace": "a" * 32,
                    "project": "foo",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "foo1",
                    "precise.start_ts": 0,
                    "precise.finish_ts": 0.012,
                },
                {
                    "trace": "a" * 32,
                    "project": "foo",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "foo1",
                    "precise.start_ts": 0.013,
                    "precise.finish_ts": 0.024,
                },
                {
                    "trace": "a" * 32,
                    "project": "foo",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "foo1",
                    "precise.start_ts": 0.032,
                    "precise.finish_ts": 0.040,
                },
            ],
            {"a" * 32: (0, 40, 4)},
            {
                "a"
                * 32: [
                    {
                        "project": "foo",
                        "sdkName": "sentry.javascript.node",
                        "start": 0,
                        "end": 20,
                        "sliceStart": 0,
                        "sliceEnd": 2,
                        "sliceWidth": 2,
                        "kind": "project",
                        "duration": 23,
                        "isRoot": False,
                    },
                    {
                        "project": "foo",
                        "sdkName": "sentry.javascript.node",
                        "start": 30,
                        "end": 40,
                        "sliceStart": 3,
                        "sliceEnd": 4,
                        "sliceWidth": 1,
                        "kind": "project",
                        "duration": 8,
                        "isRoot": False,
                    },
                ],
            },
            id="merge quantized spans",
        ),
        pytest.param(
            [
                {
                    "trace": "a" * 32,
                    "project": "foo",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "foo1",
                    "precise.start_ts": 0,
                    "precise.finish_ts": 0.1,
                },
                {
                    "trace": "a" * 32,
                    "project": "bar",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "bar1",
                    "precise.start_ts": 0.002,
                    "precise.finish_ts": 0.044,
                },
                {
                    "trace": "a" * 32,
                    "project": "foo",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "foo1",
                    "precise.start_ts": 0.007,
                    "precise.finish_ts": 0.1,
                },
            ],
            {"a" * 32: (0, 100, 5)},
            {
                "a"
                * 32: [
                    {
                        "project": "foo",
                        "sdkName": "sentry.javascript.node",
                        "start": 0,
                        "end": 100,
                        "sliceStart": 0,
                        "sliceEnd": 5,
                        "sliceWidth": 5,
                        "kind": "project",
                        "duration": 100,
                        "isRoot": False,
                    },
                    {
                        "project": "bar",
                        "sdkName": "sentry.javascript.node",
                        "start": 0,
                        "end": 40,
                        "sliceStart": 0,
                        "sliceEnd": 2,
                        "sliceWidth": 2,
                        "kind": "project",
                        "duration": 42,
                        "isRoot": False,
                    },
                ],
            },
            id="resorts spans after quantizing",
        ),
        pytest.param(
            [
                {
                    "trace": "a" * 32,
                    "project": "foo",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "foo1",
                    "precise.start_ts": 0,
                    "precise.finish_ts": 0.051,
                },
                {
                    "trace": "a" * 32,
                    "project": "foo",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "foo1",
                    "precise.start_ts": 0.069,
                    "precise.finish_ts": 0.1,
                },
            ],
            {"a" * 32: (0, 100, 5)},
            {
                "a"
                * 32: [
                    {
                        "project": "foo",
                        "sdkName": "sentry.javascript.node",
                        "start": 0,
                        "end": 100,
                        "sliceStart": 0,
                        "sliceEnd": 5,
                        "sliceWidth": 5,
                        "kind": "project",
                        "duration": 82,
                        "isRoot": False,
                    },
                ],
            },
            id="merges nearby spans",
        ),
        pytest.param(
            [
                {
                    "trace": "a" * 32,
                    "project": "foo",
                    "sdk.name": "sentry.javascript.remix",
                    "transaction": "foo1",
                    "precise.start_ts": 0,
                    "precise.finish_ts": 0.1,
                },
                {
                    "trace": "a" * 32,
                    "project": "bar",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "bar",
                    "precise.start_ts": 0.02,
                    "precise.finish_ts": 0.06,
                },
                {
                    "trace": "a" * 32,
                    "project": "foo",
                    "sdk.name": "sentry.javascript.remix",
                    "parent_span": "a" * 16,
                    "transaction": "foo1",
                    "precise.start_ts": 0.03,
                    "precise.finish_ts": 0.07,
                },
                {
                    "trace": "a" * 32,
                    "project": "bar",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "bar1",
                    "precise.start_ts": 0.04,
                    "precise.finish_ts": 0.08,
                },
                {
                    "trace": "a" * 32,
                    "project": "foo",
                    "sdk.name": "sentry.javascript.remix",
                    "parent_span": "a" * 16,
                    "transaction": "foo1",
                    "precise.start_ts": 0.05,
                    "precise.finish_ts": 0.07,
                },
            ],
            {"a" * 32: (0, 100, 10)},
            {
                "a"
                * 32: [
                    {
                        "project": "foo",
                        "sdkName": "sentry.javascript.remix",
                        "start": 0,
                        "end": 100,
                        "sliceStart": 0,
                        "sliceEnd": 10,
                        "sliceWidth": 10,
                        "kind": "project",
                        "duration": 100,
                        "isRoot": True,
                    },
                    {
                        "project": "bar",
                        "sdkName": "sentry.javascript.node",
                        "start": 20,
                        "end": 80,
                        "sliceStart": 2,
                        "sliceEnd": 8,
                        "sliceWidth": 6,
                        "kind": "project",
                        "duration": 60,
                        "isRoot": False,
                    },
                    {
                        "project": "foo",
                        "sdkName": "sentry.javascript.remix",
                        "start": 30,
                        "end": 70,
                        "sliceStart": 3,
                        "sliceEnd": 7,
                        "sliceWidth": 4,
                        "kind": "project",
                        "duration": 40,
                        "isRoot": False,
                    },
                ],
            },
            id="merges spans at different depths",
        ),
        pytest.param(
            [
                {
                    "trace": "a" * 32,
                    "project": "foo",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "foo1",
                    "precise.start_ts": 0.003,
                    "precise.finish_ts": 0.097,
                },
                {
                    "trace": "a" * 32,
                    "project": "foo",
                    "sdk.name": "sentry.javascript.remix",
                    "parent_span": "a" * 16,
                    "transaction": "foo1",
                    "precise.start_ts": 0.002,
                    "precise.finish_ts": 0.098,
                },
            ],
            {"a" * 32: (0, 100, 10)},
            {
                "a"
                * 32: [
                    {
                        "project": "foo",
                        "sdkName": "sentry.javascript.remix",
                        "start": 0,
                        "end": 100,
                        "sliceStart": 0,
                        "sliceEnd": 10,
                        "sliceWidth": 10,
                        "kind": "project",
                        "duration": 96,
                        "isRoot": False,
                    },
                    {
                        "project": "foo",
                        "sdkName": "sentry.javascript.node",
                        "start": 0,
                        "end": 100,
                        "sliceStart": 0,
                        "sliceEnd": 10,
                        "sliceWidth": 10,
                        "kind": "project",
                        "duration": 94,
                        "isRoot": False,
                    },
                ],
            },
            id="orders spans by precise timestamps",
        ),
        pytest.param(
            [
                {
                    "trace": "a" * 32,
                    "project": "foo",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "foo1",
                    "precise.start_ts": 0.003,
                    "precise.finish_ts": 0.097,
                },
                {
                    "trace": "a" * 32,
                    "project": "foo",
                    "sdk.name": "sentry.javascript.remix",
                    "parent_span": "a" * 16,
                    "transaction": "foo1",
                    "precise.start_ts": 0.002,
                    "precise.finish_ts": 0.098,
                },
            ],
            {"a" * 32: (0, 100, 1000)},
            {
                "a"
                * 32: [
                    {
                        "project": "foo",
                        "sdkName": "sentry.javascript.remix",
                        "start": 2,
                        "end": 98,
                        "sliceStart": 20,
                        "sliceEnd": 980,
                        "sliceWidth": 960,
                        "kind": "project",
                        "duration": 96,
                        "isRoot": False,
                    },
                    {
                        "project": "foo",
                        "sdkName": "sentry.javascript.node",
                        "start": 3,
                        "end": 97,
                        "sliceStart": 30,
                        "sliceEnd": 970,
                        "sliceWidth": 940,
                        "kind": "project",
                        "duration": 94,
                        "isRoot": False,
                    },
                ],
            },
            id="trace shorter than slices",
        ),
        pytest.param(
            [
                {
                    "trace": "a" * 32,
                    "project": "foo",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "foo1",
                    "precise.start_ts": 1,
                    "precise.finish_ts": 1,
                },
            ],
            {"a" * 32: (1, 1, 40)},
            {
                "a"
                * 32: [
                    {
                        "project": "foo",
                        "sdkName": "sentry.javascript.node",
                        "start": 1,
                        "end": 1,
                        "sliceStart": 0,
                        "sliceEnd": 40,
                        "sliceWidth": 40,
                        "kind": "project",
                        "duration": 0,
                        "isRoot": False,
                    },
                ],
            },
            id="zero duration trace",
        ),
        pytest.param(
            [
                {
                    "trace": "a" * 32,
                    "project": "foo",
                    "sdk.name": "sentry.javascript.remix",
                    "parent_span": "a" * 16,
                    "transaction": "foo1",
                    "precise.start_ts": 0.0,
                    "precise.finish_ts": 0.04,
                },
                {
                    "trace": "a" * 32,
                    "project": "foo",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "foo1",
                    "precise.start_ts": 0.000,
                    "precise.finish_ts": 0.001,
                },
                {
                    "trace": "a" * 32,
                    "project": "foo",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "foo1",
                    "precise.start_ts": 0.029,
                    "precise.finish_ts": 0.031,
                },
                {
                    "trace": "a" * 32,
                    "project": "foo",
                    "sdk.name": "sentry.javascript.node",
                    "parent_span": "a" * 16,
                    "transaction": "foo1",
                    "precise.start_ts": 0.039,
                    "precise.finish_ts": 0.040,
                },
            ],
            {"a" * 32: (0, 40, 4)},
            {
                "a"
                * 32: [
                    {
                        "project": "foo",
                        "sdkName": "sentry.javascript.remix",
                        "start": 0,
                        "end": 40,
                        "sliceStart": 0,
                        "sliceEnd": 4,
                        "sliceWidth": 4,
                        "kind": "project",
                        "duration": 40,
                        "isRoot": False,
                    },
                    {
                        "project": "foo",
                        "sdkName": "sentry.javascript.node",
                        "start": 0,
                        "end": 10,
                        "sliceStart": 0,
                        "sliceEnd": 1,
                        "sliceWidth": 1,
                        "kind": "project",
                        "duration": 1,
                        "isRoot": False,
                    },
                    {
                        "project": "foo",
                        "sdkName": "sentry.javascript.node",
                        "start": 30,
                        "end": 40,
                        "sliceStart": 3,
                        "sliceEnd": 4,
                        "sliceWidth": 1,
                        "kind": "project",
                        "duration": 2,
                        "isRoot": False,
                    },
                ],
            },
            id="expand narrow slice",
        ),
    ],
)
def test_process_breakdowns(data, traces_range, expected) -> None:
    traces_range = {
        trace: {
            "start": trace_start,
            "end": trace_end,
            "slices": trace_slices,
        }
        for trace, (trace_start, trace_end, trace_slices) in traces_range.items()
    }
    result = process_breakdowns(data, traces_range)
    assert result == expected


@patch("sentry_sdk.capture_exception")
@patch("sentry.api.endpoints.organization_traces.quantize_range")
def test_quantize_range_error(
    mock_quantize_range: MagicMock, mock_capture_exception: MagicMock
) -> None:
    exception = Exception()

    mock_quantize_range.side_effect = exception

    data = [
        {
            "trace": "a" * 32,
            "project": "foo",
            "sdk.name": "sentry.javascript.node",
            "parent_span": "a" * 16,
            "transaction": "foo1",
            "precise.start_ts": 0,
            "precise.finish_ts": 0.1,
        },
    ]
    traces_range = {
        "a"
        * 32: {
            "start": 0,
            "end": 100,
            "slices": 0,
        }
    }
    result = process_breakdowns(data, traces_range)
    assert result == {"a" * 32: []}

    mock_capture_exception.assert_called_with(
        exception, contexts={"bad_trace": {"trace": "a" * 32}}
    )


@patch("sentry_sdk.capture_exception")
@patch("sentry.api.endpoints.organization_traces.new_trace_interval")
def test_build_breakdown_error(
    mock_new_trace_interval: MagicMock, mock_capture_exception: MagicMock
) -> None:
    exception = Exception()

    mock_new_trace_interval.side_effect = exception

    data = [
        {
            "trace": "a" * 32,
            "project": "foo",
            "sdk.name": "sentry.javascript.node",
            "parent_span": "a" * 16,
            "transaction": "foo1",
            "precise.start_ts": 0,
            "precise.finish_ts": 0.1,
        },
    ]
    traces_range = {
        "a"
        * 32: {
            "start": 0,
            "end": 100,
            "slices": 10,
        }
    }
    result = process_breakdowns(data, traces_range)
    assert result == {"a" * 32: []}

    mock_capture_exception.assert_called_with(
        exception, contexts={"bad_trace": {"trace": "a" * 32}}
    )
