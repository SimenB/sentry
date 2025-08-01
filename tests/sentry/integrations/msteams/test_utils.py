import time

import orjson
import responses

from sentry.integrations.msteams.utils import get_channel_id
from sentry.testutils.cases import TestCase
from sentry.testutils.skips import requires_snuba

pytestmark = [requires_snuba]


class GetChannelIdTest(TestCase):
    def setUp(self) -> None:
        responses.reset()

        self.integration, _ = self.create_provider_integration_for(
            self.event.project.organization,
            self.user,
            provider="msteams",
            name="Brute Squad",
            external_id="3x73rna1-id",
            metadata={
                "service_url": "https://smba.trafficmanager.net/amer",
                "access_token": "inc0nc3iv4b13",
                "expires_at": int(time.time()) + 86400,
            },
        )
        channels = [
            {"id": "g_c"},
            {"id": "p_o_d", "name": "Pit of Despair"},
        ]
        first_users = [
            {"name": "Wesley", "id": "d_p_r", "tenantId": "3141-5926-5358"},
            {"name": "Buttercup", "id": "p_b", "tenantId": "2718-2818-2845"},
        ]
        second_users = [{"name": "Inigo", "id": "p_t_d", "tenantId": "1618-0339-8874"}]
        responses.add(
            responses.GET,
            "https://smba.trafficmanager.net/amer/v3/teams/3x73rna1-id/conversations",
            json={"conversations": channels},
        )
        responses.add(
            responses.GET,
            "https://smba.trafficmanager.net/amer/v3/conversations/3x73rna1-id/pagedmembers?pageSize=500",
            json={"members": first_users, "continuationToken": "con71nu3"},
        )
        responses.add(
            responses.GET,
            "https://smba.trafficmanager.net/amer/v3/conversations/3x73rna1-id/pagedmembers?pageSize=500&continuationToken=con71nu3",
            json={"members": second_users},
        )

        def user_conversation_id_callback(request):
            payload = orjson.loads(request.body)
            if payload["members"] == [{"id": "d_p_r"}] and payload["channelData"] == {
                "tenant": {"id": "3141-5926-5358"}
            }:
                return 200, {}, orjson.dumps({"id": "dread_pirate_roberts"}).decode()
            elif payload["members"] == [{"id": "p_b"}] and payload["channelData"] == {
                "tenant": {"id": "2718-2818-2845"}
            }:
                return 200, {}, orjson.dumps({"id": "princess_bride"}).decode()
            elif payload["members"] == [{"id": "p_t_d"}] and payload["channelData"] == {
                "tenant": {"id": "1618-0339-8874"}
            }:
                return 200, {}, orjson.dumps({"id": "prepare_to_die"}).decode()

        responses.add_callback(
            responses.POST,
            "https://smba.trafficmanager.net/amer/v3/conversations",
            callback=user_conversation_id_callback,
        )

    @responses.activate
    def run_valid_test(self, expected, name):
        assert expected == get_channel_id(self.organization, self.integration.id, name)

    @responses.activate
    def run_invalid_test(self, name):
        assert get_channel_id(self.organization, self.integration.id, name) is None

    def test_general_channel_selected(self) -> None:
        self.run_valid_test("g_c", "general")

    def test_other_channel_selected(self) -> None:
        self.run_valid_test("p_o_d", "pit of Despair")

    def test_bad_channel_not_selected(self) -> None:
        self.run_invalid_test("Cliffs of Insanity")

    def test_user_selected(self) -> None:
        self.run_valid_test("dread_pirate_roberts", "Wesley")

    def test_other_user_selected(self) -> None:
        self.run_valid_test("princess_bride", "Buttercup")

    def test_other_user_selected_continuation(self) -> None:
        self.run_valid_test("prepare_to_die", "Inigo")

    def test_bad_user_not_selected(self) -> None:
        self.run_invalid_test("Prince Humperdinck")
