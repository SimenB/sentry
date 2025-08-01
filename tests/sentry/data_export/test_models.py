import tempfile
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.core import mail
from django.urls import reverse
from django.utils import timezone

from sentry.data_export.base import DEFAULT_EXPIRATION, ExportQueryType, ExportStatus
from sentry.data_export.models import ExportedData
from sentry.models.files.file import File
from sentry.testutils.cases import TestCase
from sentry.testutils.helpers.features import with_feature
from sentry.utils import json
from sentry.utils.http import absolute_uri


class ExportedDataTest(TestCase):
    TEST_STRING = b"A bunch of test data..."

    def setUp(self) -> None:
        super().setUp()
        self.user = self.create_user()
        self.organization = self.create_organization()
        self.data_export = ExportedData.objects.create(
            user_id=self.user.id,
            organization=self.organization,
            query_type=0,
            query_info={"env": "test"},
        )
        self.file1 = File.objects.create(
            name="tempfile-data-export", type="export.csv", headers={"Content-Type": "text/csv"}
        )
        self.file2 = File.objects.create(
            name="tempfile-data-export", type="export.csv", headers={"Content-Type": "text/csv"}
        )

    def test_status_property(self) -> None:
        def _assert_status(status: ExportStatus) -> None:
            assert self.data_export.status == status

        _assert_status(ExportStatus.Early)
        self.data_export.update(
            date_expired=timezone.now() + timedelta(weeks=2),
            date_finished=timezone.now() - timedelta(weeks=2),
        )
        _assert_status(ExportStatus.Valid)
        self.data_export.update(date_expired=timezone.now() - timedelta(weeks=1))
        _assert_status(ExportStatus.Expired)

    def test_payload_property(self) -> None:
        assert isinstance(self.data_export.payload, dict)
        keys = list(self.data_export.query_info.keys()) + ["export_type"]
        assert sorted(self.data_export.payload.keys()) == sorted(keys)

    def test_file_name_property(self) -> None:
        assert isinstance(self.data_export.file_name, str)
        file_name = self.data_export.file_name
        assert file_name.startswith(ExportQueryType.as_str(self.data_export.query_type))
        assert file_name.endswith(str(self.data_export.id) + ".csv")

    def test_format_date(self) -> None:
        assert ExportedData.format_date(self.data_export.date_finished) is None
        assert isinstance(ExportedData.format_date(self.data_export.date_added), str)

    def test_delete_file(self) -> None:
        # Empty call should have no effect
        assert self.data_export.file_id is None
        self.data_export.delete_file()
        assert self.data_export.file_id is None
        # Real call should delete the file
        assert File.objects.filter(id=self.file1.id).exists()
        self.data_export.update(file_id=self.file1.id)
        assert isinstance(self.data_export._get_file(), File)
        self.data_export.delete_file()
        assert self.data_export._get_file() is None
        assert not File.objects.filter(id=self.file1.id).exists()
        # The ExportedData should be unaffected
        assert ExportedData.objects.filter(id=self.data_export.id).exists()
        assert ExportedData.objects.get(id=self.data_export.id)._get_file() is None

    def test_delete(self) -> None:
        self.data_export.finalize_upload(file=self.file1)
        assert ExportedData.objects.filter(id=self.data_export.id).exists()
        assert File.objects.filter(id=self.file1.id).exists()
        self.data_export.delete()
        assert not ExportedData.objects.filter(id=self.data_export.id).exists()
        assert not File.objects.filter(id=self.file1.id).exists()

    def test_finalize_upload(self) -> None:
        # With default expiration
        with tempfile.TemporaryFile() as tf:
            tf.write(self.TEST_STRING)
            tf.seek(0)
            self.file1.putfile(tf)
        self.data_export.finalize_upload(file=self.file1)
        assert self.data_export._get_file().getfile().read() == self.TEST_STRING
        assert self.data_export.date_finished is not None
        assert self.data_export.date_expired is not None
        assert self.data_export.date_expired == self.data_export.date_finished + DEFAULT_EXPIRATION
        # With custom expiration
        with tempfile.TemporaryFile() as tf:
            tf.write(self.TEST_STRING + self.TEST_STRING)
            tf.seek(0)
            self.file2.putfile(tf)
        self.data_export.finalize_upload(file=self.file2, expiration=timedelta(weeks=2))
        assert self.data_export._get_file().getfile().read() == self.TEST_STRING + self.TEST_STRING
        # Ensure the first file is deleted
        assert not File.objects.filter(id=self.file1.id).exists()
        assert self.data_export.date_expired == self.data_export.date_finished + timedelta(weeks=2)

    def test_email_success(self) -> None:
        # Shouldn't send if ExportedData is incomplete
        with self.tasks():
            self.data_export.email_success()
        assert len(mail.outbox) == 0
        # Should send one email if complete
        self.data_export.finalize_upload(file=self.file1)
        with self.tasks():
            self.data_export.email_success()
        assert len(mail.outbox) == 1

    @with_feature("system:multi-region")
    def test_email_success_customer_domains(self) -> None:
        self.data_export.finalize_upload(file=self.file1)
        with self.tasks():
            self.data_export.email_success()
        assert len(mail.outbox) == 1
        msg = mail.outbox[0]
        assert msg.subject == "Your data is ready."
        assert (
            self.organization.absolute_url(f"/organizations/{self.organization.slug}/data-export/")
            in msg.body
        )

    @patch("sentry.utils.email.MessageBuilder")
    def test_email_success_content(self, builder: MagicMock) -> None:
        self.data_export.finalize_upload(file=self.file1)
        with self.tasks():
            self.data_export.email_success()
        expected_url = absolute_uri(
            reverse(
                "sentry-data-export-details", args=[self.organization.slug, self.data_export.id]
            )
        )
        expected_email_args = {
            "subject": "Your data is ready.",
            "context": {
                "url": expected_url,
                "expiration": ExportedData.format_date(date=self.data_export.date_expired),
            },
            "type": "organization.export-data",
            "template": "sentry/emails/data-export-success.txt",
            "html_template": "sentry/emails/data-export-success.html",
        }
        builder.assert_called_with(**expected_email_args)

    def test_email_failure(self) -> None:
        with self.tasks():
            self.data_export.email_failure("failed to export data!")
        assert len(mail.outbox) == 1
        assert not ExportedData.objects.filter(id=self.data_export.id).exists()

    @patch("sentry.utils.email.MessageBuilder")
    def test_email_failure_content(self, builder: MagicMock) -> None:
        with self.tasks():
            self.data_export.email_failure("failed to export data!")
        expected_email_args = {
            "subject": "We couldn't export your data.",
            "context": {
                "creation": ExportedData.format_date(date=self.data_export.date_added),
                "error_message": "failed to export data!",
                "payload": json.dumps(self.data_export.payload),
            },
            "type": "organization.export-data",
            "template": "sentry/emails/data-export-failure.txt",
            "html_template": "sentry/emails/data-export-failure.html",
        }
        builder.assert_called_with(**expected_email_args)
