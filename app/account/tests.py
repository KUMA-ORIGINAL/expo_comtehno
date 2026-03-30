from itertools import count
from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.translation import override

from account.admin.registration import RegistrationCampaignAdmin, RegistrationSubmissionAdmin
from account.models import ExhibitionVisitor, RegistrationCampaign, RegistrationField, RegistrationSubmission
from account.registration_forms import build_dynamic_registration_form_class
from account.ticket_utils import ensure_submission_ticket_token, submission_ticket_code, visitor_ticket_code


_PHONE_COUNTER = count(1)


def create_test_user(email, password="pass1234", **extra_fields):
    User = get_user_model()
    extra_fields.setdefault("phone_number", f"+996700{next(_PHONE_COUNTER):06d}")
    return User.objects.create_user(email=email, password=password, **extra_fields)


def create_test_superuser(email, password="pass1234", **extra_fields):
    User = get_user_model()
    extra_fields.setdefault("phone_number", f"+996700{next(_PHONE_COUNTER):06d}")
    return User.objects.create_superuser(email=email, password=password, **extra_fields)


class RegistrationCampaignAdminOwnershipTests(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.factory = RequestFactory()
        self.campaign_admin = RegistrationCampaignAdmin(RegistrationCampaign, self.site)
        self.submission_admin = RegistrationSubmissionAdmin(RegistrationSubmission, self.site)
        self.superuser = create_test_superuser("root@example.com")
        self.owner = create_test_user("owner@example.com", is_staff=True)
        self.other = create_test_user("other@example.com", is_staff=True)
        self.owner_campaign = RegistrationCampaign.objects.create(
            owner=self.owner,
            slug="owner-campaign",
            title="Owner campaign",
            is_active=True,
        )
        self.other_campaign = RegistrationCampaign.objects.create(
            owner=self.other,
            slug="other-campaign",
            title="Other campaign",
            is_active=True,
        )
        RegistrationField.objects.create(
            campaign=self.owner_campaign,
            key="full_name",
            label="Full name",
            field_type=RegistrationField.TYPE_TEXT,
            required=True,
            sort_order=1,
        )
        self.owner_submission = RegistrationSubmission.objects.create(
            campaign=self.owner_campaign,
            data={"full_name": "John Owner"},
            applicant_name="John Owner",
        )
        self.other_submission = RegistrationSubmission.objects.create(
            campaign=self.other_campaign,
            data={"full_name": "Mike Other"},
            applicant_name="Mike Other",
        )

    def _request_for(self, user):
        request = self.factory.get("/admin/")
        request.user = user
        return request

    def test_staff_sees_only_own_campaigns(self):
        qs = self.campaign_admin.get_queryset(self._request_for(self.owner))
        self.assertEqual(list(qs), [self.owner_campaign])

    def test_superuser_sees_all_campaigns(self):
        qs = self.campaign_admin.get_queryset(self._request_for(self.superuser))
        self.assertIn(self.owner_campaign, qs)
        self.assertIn(self.other_campaign, qs)

    def test_staff_sees_only_own_submissions(self):
        qs = self.submission_admin.get_queryset(self._request_for(self.owner))
        self.assertEqual(list(qs), [self.owner_submission])

    def test_admin_sets_owner_on_create(self):
        request = self._request_for(self.owner)
        campaign = RegistrationCampaign(
            slug="autowned-campaign",
            title="Autowned campaign",
            is_active=True,
        )
        self.campaign_admin.save_model(request, campaign, form=None, change=False)
        campaign.refresh_from_db()
        self.assertEqual(campaign.owner_id, self.owner.id)


class RegistrationMultilanguageFlowTests(TestCase):
    def setUp(self):
        self.owner = create_test_user("owner2@example.com", is_staff=True)
        self.campaign = RegistrationCampaign.objects.create(
            owner=self.owner,
            slug="lang-campaign",
            title="Русский заголовок",
            title_ru="Русский заголовок",
            title_en="English title",
            subtitle_ru="Русский подзаголовок",
            subtitle_en="English subtitle",
            applicant_name_field_keys="full_name",
            participation_terms_ru="Русские условия",
            participation_terms_en="English terms",
            allow_duplicate_submissions=True,
            send_applicant_confirmation=False,
            notify_staff=False,
            is_active=True,
        )
        RegistrationField.objects.create(
            campaign=self.campaign,
            key="full_name",
            label="ФИО",
            label_ru="ФИО",
            label_en="Full name",
            field_type=RegistrationField.TYPE_TEXT,
            required=True,
            sort_order=1,
        )

    def test_form_uses_english_translation_and_terms(self):
        response = self.client.get(
            reverse("registration_form", kwargs={"slug": self.campaign.slug}),
            HTTP_ACCEPT_LANGUAGE="en",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "English title")
        self.assertContains(response, "Full name")
        self.assertContains(response, "English terms")

    def test_fallback_to_ru_when_english_is_missing(self):
        self.campaign.title_en = ""
        self.campaign.save(update_fields=["title_en"])
        with override("en"):
            self.assertEqual(self.campaign.title, "Русский заголовок")

    def test_submission_saves_language_and_ticket_print_is_localized(self):
        response = self.client.post(
            reverse("registration_form", kwargs={"slug": self.campaign.slug}),
            data={"full_name": "John Snow"},
            HTTP_ACCEPT_LANGUAGE="en",
        )
        self.assertEqual(response.status_code, 302)
        submission = RegistrationSubmission.objects.get(campaign=self.campaign)
        self.assertEqual(submission.language_code, "en")

        token = ensure_submission_ticket_token(submission)
        print_response = self.client.get(reverse("exhibition_ticket_print", kwargs={"token": token}))
        self.assertEqual(print_response.status_code, 200)
        self.assertContains(print_response, "John Snow")


class RegistrationReliabilityTests(TestCase):
    def setUp(self):
        self.owner = create_test_user("owner3@example.com", is_staff=True)
        self.campaign = RegistrationCampaign.objects.create(
            owner=self.owner,
            slug="reliable-campaign",
            title="Reliable campaign",
            applicant_email_field_key="contact_email",
            applicant_name_field_keys="full_name",
            send_applicant_confirmation=False,
            notify_staff=False,
            is_active=True,
        )
        RegistrationField.objects.create(
            campaign=self.campaign,
            key="full_name",
            label="Full name",
            field_type=RegistrationField.TYPE_TEXT,
            required=True,
            sort_order=1,
        )
        RegistrationField.objects.create(
            campaign=self.campaign,
            key="contact_email",
            label="Email",
            field_type=RegistrationField.TYPE_EMAIL,
            required=True,
            sort_order=2,
        )

    @override_settings(REGISTRATION_EMAIL_VIA_CELERY=False)
    def test_registration_succeeds_even_if_email_delivery_fails(self):
        with patch("common.tasks.deliver_registration_submission_emails", side_effect=RuntimeError("smtp down")) as mocked:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    reverse("registration_form", kwargs={"slug": self.campaign.slug}),
                    data={"full_name": "John Snow", "contact_email": "john@example.com"},
                )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(RegistrationSubmission.objects.filter(campaign=self.campaign).count(), 1)
        mocked.assert_called_once()

    def test_duplicate_submission_is_blocked_case_insensitively(self):
        first_response = self.client.post(
            reverse("registration_form", kwargs={"slug": self.campaign.slug}),
            data={"full_name": "John Snow", "contact_email": "John@example.com"},
        )
        self.assertEqual(first_response.status_code, 302)

        second_response = self.client.post(
            reverse("registration_form", kwargs={"slug": self.campaign.slug}),
            data={"full_name": "John Snow", "contact_email": "john@example.com"},
        )
        self.assertEqual(second_response.status_code, 200)
        self.assertContains(second_response, "уже подана заявка", status_code=200)
        self.assertEqual(RegistrationSubmission.objects.filter(campaign=self.campaign).count(), 1)


    def test_radio_other_value_is_saved_as_custom_text(self):
        campaign = RegistrationCampaign.objects.create(
            owner=self.owner,
            slug="radio-other-campaign",
            title="Radio other campaign",
            applicant_name_field_keys="attendance_format",
            allow_duplicate_submissions=True,
            send_applicant_confirmation=False,
            notify_staff=False,
            is_active=True,
        )
        RegistrationField.objects.create(
            campaign=campaign,
            key="attendance_format",
            label="Форма участия",
            field_type=RegistrationField.TYPE_RADIO,
            choices_text="onsite|Очная\nonline|Дистанционная",
            required=True,
            sort_order=1,
        )

        response = self.client.post(
            reverse("registration_form", kwargs={"slug": campaign.slug}),
            data={
                "attendance_format": "__other__",
                "attendance_format__other": "Гибридная",
            },
        )
        self.assertEqual(response.status_code, 302)

        submission = RegistrationSubmission.objects.get(campaign=campaign)
        self.assertEqual(submission.data.get("attendance_format"), "Гибридная")
        self.assertNotIn("attendance_format__other", submission.data)


class RegistrationConfigurationTests(TestCase):
    def setUp(self):
        self.owner = create_test_user("owner4@example.com", is_staff=True)

    def test_builder_rejects_wrong_email_field_type(self):
        campaign = RegistrationCampaign.objects.create(
            owner=self.owner,
            slug="broken-campaign",
            title="Broken campaign",
            applicant_email_field_key="full_name",
            applicant_name_field_keys="full_name",
            send_applicant_confirmation=True,
            notify_staff=False,
            is_active=True,
        )
        RegistrationField.objects.create(
            campaign=campaign,
            key="full_name",
            label="Full name",
            field_type=RegistrationField.TYPE_TEXT,
            required=True,
            sort_order=1,
        )

        with self.assertRaises(ValidationError):
            build_dynamic_registration_form_class(campaign)

    def test_misconfigured_campaign_returns_503_in_public_view(self):
        campaign = RegistrationCampaign.objects.create(
            owner=self.owner,
            slug="broken-public-campaign",
            title="Broken public campaign",
            applicant_email_field_key="contact_email",
            applicant_name_field_keys="full_name",
            send_applicant_confirmation=True,
            notify_staff=False,
            is_active=True,
        )
        RegistrationField.objects.create(
            campaign=campaign,
            key="full_name",
            label="Full name",
            field_type=RegistrationField.TYPE_TEXT,
            required=True,
            sort_order=1,
        )

        response = self.client.get(reverse("registration_form", kwargs={"slug": campaign.slug}))
        self.assertEqual(response.status_code, 503)
        self.assertContains(response, "временно недоступна", status_code=503)


class TicketCheckinTests(TestCase):
    def setUp(self):
        self.staff = create_test_user("staff1@example.com", is_staff=True)
        self.owner = create_test_user("owner5@example.com", is_staff=True)
        self.client.force_login(self.staff)

        self.campaign = RegistrationCampaign.objects.create(
            owner=self.owner,
            slug="checkin-campaign",
            title="Check-in campaign",
            applicant_email_field_key="contact_email",
            applicant_name_field_keys="full_name",
            send_applicant_confirmation=False,
            notify_staff=False,
            is_active=True,
        )
        RegistrationField.objects.create(
            campaign=self.campaign,
            key="full_name",
            label="Full name",
            field_type=RegistrationField.TYPE_TEXT,
            required=True,
            sort_order=1,
        )
        RegistrationField.objects.create(
            campaign=self.campaign,
            key="contact_email",
            label="Email",
            field_type=RegistrationField.TYPE_EMAIL,
            required=True,
            sort_order=2,
        )
        self.submission = RegistrationSubmission.objects.create(
            campaign=self.campaign,
            data={"full_name": "Jane Doe", "contact_email": "jane@example.com"},
            applicant_name="Jane Doe",
            applicant_email="jane@example.com",
        )
        self.visitor = ExhibitionVisitor.objects.create(
            email="visitor@example.com",
            last_name="Visitor",
            first_name="Legacy",
            middle_name="Flow",
            phone_number="+996700000001",
            city="Bishkek",
            company="ICEE",
            exhibition_theme="construction",
            industry="construction",
            position="manager",
            visit_purposes=["info"],
            source="internet",
            personal_data_consent=True,
        )

    def test_staff_can_resolve_submission_ticket_code(self):
        response = self.client.post(
            reverse("exhibition_checkin"),
            data={"ticket_code": submission_ticket_code(self.submission.id)},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["submission"].id, self.submission.id)
        self.assertIsNone(response.context["visitor"])

    def test_staff_can_resolve_visitor_ticket_code(self):
        response = self.client.post(
            reverse("exhibition_checkin"),
            data={"ticket_code": visitor_ticket_code(self.visitor.id)},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["visitor"].id, self.visitor.id)
        self.assertIsNone(response.context["submission"])
