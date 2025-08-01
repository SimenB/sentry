from unittest.mock import MagicMock, patch

from django.core.signing import SignatureExpired

from sentry.integrations.msteams.constants import SALT
from sentry.integrations.web.msteams_extension_configuration import (
    MsTeamsExtensionConfigurationView,
)
from sentry.models.organizationmember import OrganizationMember
from sentry.silo.base import SiloMode
from sentry.testutils.cases import TestCase
from sentry.testutils.silo import assume_test_silo_mode, control_silo_test
from sentry.utils.signing import sign


@control_silo_test
class MsTeamsExtensionConfigurationTest(TestCase):
    def hit_configure(self, params):
        self.login_as(self.user)
        org = self.create_organization()
        with assume_test_silo_mode(SiloMode.REGION):
            OrganizationMember.objects.create(user_id=self.user.id, organization=org, role="admin")
        path = "/extensions/msteams/configure/"
        return self.client.get(path, params)

    def test_map_params(self) -> None:
        config_view = MsTeamsExtensionConfigurationView()
        data = {"my_param": "test"}
        signed_data = sign(salt=SALT, **data)
        params = {"signed_params": signed_data}
        assert data == config_view.map_params_to_state(params)

    @patch("sentry.integrations.web.msteams_extension_configuration.unsign")
    def test_expired_signature(self, mock_unsign: MagicMock) -> None:
        with self.feature({"organizations:integrations-alert-rule": True}):
            mock_unsign.side_effect = SignatureExpired()
            resp = self.hit_configure({"signed_params": "test"})
            assert b"Installation link expired" in resp.content

    def test_no_team_plan_feature_flag(self) -> None:
        with self.feature(
            {
                "organizations:integrations-alert-rule": False,
                "organizations:integrations-chat-unfurl": False,
            }
        ):
            resp = self.hit_configure({"signed_params": "test"})
            assert resp.status_code == 302
            assert "/extensions/msteams/link/" in resp.url
