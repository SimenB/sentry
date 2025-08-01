from datetime import datetime
from unittest import mock

from arroyo.backends.kafka import KafkaPayload
from arroyo.types import BrokerValue, Message, Partition
from arroyo.types import Topic as ArroyoTopic
from sentry_protos.snuba.v1.trace_item_pb2 import TraceItem

from sentry.conf.types.kafka_definition import Topic
from sentry.spans.consumers.process_segments.convert import convert_span_to_item
from sentry.spans.consumers.process_segments.factory import DetectPerformanceIssuesStrategyFactory
from sentry.testutils.helpers.options import override_options
from sentry.utils import json
from sentry.utils.kafka_config import get_topic_definition
from tests.sentry.spans.consumers.process import build_mock_span


def build_mock_message(data, topic=None):
    message = mock.Mock()
    message.value.return_value = json.dumps(data)
    if topic:
        message.topic.return_value = topic
    return message


@override_options({"spans.process-segments.consumer.enable": True})
@mock.patch(
    "sentry.spans.consumers.process_segments.factory.process_segment",
    side_effect=lambda x, **kwargs: x,
)
def test_segment_deserialized_correctly(mock_process_segment: mock.MagicMock) -> None:
    topic = ArroyoTopic(get_topic_definition(Topic.BUFFERED_SEGMENTS)["real_topic_name"])
    partition_1 = Partition(topic, 0)
    partition_2 = Partition(topic, 1)
    mock_commit = mock.Mock()
    factory = DetectPerformanceIssuesStrategyFactory(
        num_processes=2,
        input_block_size=1,
        max_batch_size=2,
        max_batch_time=1,
        output_block_size=1,
        skip_produce=False,
    )

    with mock.patch.object(factory, "producer", new=mock.Mock()) as mock_producer:
        strategy = factory.create_with_partitions(
            commit=mock_commit,
            partitions={},
        )

        span_data = build_mock_span(project_id=1, is_segment=True)
        segment_data = {"spans": [span_data]}
        message = build_mock_message(segment_data, topic)

        strategy.submit(
            Message(
                BrokerValue(
                    KafkaPayload(b"key", message.value().encode("utf-8"), []),
                    partition_1,
                    1,
                    datetime.now(),
                )
            )
        )

        strategy.submit(
            Message(
                BrokerValue(
                    KafkaPayload(b"key", message.value().encode("utf-8"), []),
                    partition_2,
                    1,
                    datetime.now(),
                )
            )
        )

        strategy.poll()
        strategy.join(1)
        strategy.terminate()

        calls = [
            mock.call({partition_1: 2}),
            mock.call({partition_2: 2}),
        ]
        mock_commit.assert_has_calls(calls=calls, any_order=True)

        assert mock_process_segment.call_args.args[0] == segment_data["spans"]

        assert mock_producer.produce.call_count == 2
        assert mock_producer.produce.call_args.args[0] == ArroyoTopic("snuba-items")

        payload = mock_producer.produce.call_args.args[1]
        span_item = TraceItem.FromString(payload.value)
        assert span_item == convert_span_to_item(span_data)

        headers = {k: v for k, v in payload.headers}
        assert headers["item_type"] == b"1"
        assert headers["project_id"] == b"1"
