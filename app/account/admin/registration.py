from types import SimpleNamespace

from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.forms.models import BaseInlineFormSet
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _
from modeltranslation.admin import TabbedTranslationAdmin, TranslationStackedInline
from unfold.admin import StackedInline
from unfold.contrib.forms.widgets import WysiwygWidget

from account.models import RegistrationCampaign, RegistrationEmailSender, RegistrationField, RegistrationSubmission
from common.base_admin import BaseModelAdmin
from common.tasks import queue_registration_submission_emails


class RegistrationFieldInlineFormSet(BaseInlineFormSet):
    TRUE_VALUES = {"1", "true", "on", "yes"}
    FIELD_LABELS = {
        "applicant_email_field_key": _("Ключ поля с email заявителя"),
        "applicant_name_field_keys": _("Ключи имени заявителя"),
        "ticket_pdf_field_keys": _("Доп. поля электронного билета"),
        "ticket_print_field_keys": _("Доп. поля печатного билета"),
        "staff_notification_emails": _("Email организаторов"),
        "is_active": _("Статус формы"),
        "__all__": _("Конфигурация формы"),
    }

    def _bool_from_data(self, key, default):
        if key not in self.data:
            return False
        raw = self.data.get(key)
        return str(raw).strip().lower() in self.TRUE_VALUES

    def clean(self):
        super().clean()
        if any(self.errors):
            return

        field_defs = []
        seen_keys = set()
        duplicate_keys = set()

        for form in self.forms:
            cleaned = getattr(form, "cleaned_data", None)
            if not cleaned or cleaned.get("DELETE"):
                continue
            key = (cleaned.get("key") or "").strip()
            if not key:
                continue
            if key in seen_keys:
                duplicate_keys.add(key)
            else:
                seen_keys.add(key)
            field_defs.append(SimpleNamespace(key=key, field_type=cleaned.get("field_type")))

        if duplicate_keys:
            raise ValidationError(
                _("Ключи полей должны быть уникальны: {keys}").format(keys=", ".join(sorted(duplicate_keys)))
            )

        campaign = self.instance
        campaign.applicant_email_field_key = (
            self.data.get("applicant_email_field_key", campaign.applicant_email_field_key) or ""
        ).strip()
        campaign.applicant_name_field_keys = (
            self.data.get("applicant_name_field_keys", campaign.applicant_name_field_keys) or ""
        ).strip()
        campaign.ticket_pdf_field_keys = (
            self.data.get("ticket_pdf_field_keys", campaign.ticket_pdf_field_keys) or ""
        ).strip()
        campaign.ticket_print_field_keys = (
            self.data.get("ticket_print_field_keys", campaign.ticket_print_field_keys) or ""
        ).strip()
        campaign.staff_notification_emails = self.data.get(
            "staff_notification_emails",
            campaign.staff_notification_emails,
        )
        campaign.staff_notification_emails = campaign.normalize_staff_notification_emails(
            campaign.staff_notification_emails
        )
        campaign.send_applicant_confirmation = self._bool_from_data(
            "send_applicant_confirmation",
            campaign.send_applicant_confirmation,
        )
        campaign.allow_duplicate_submissions = self._bool_from_data(
            "allow_duplicate_submissions",
            campaign.allow_duplicate_submissions,
        )
        campaign.notify_staff = self._bool_from_data("notify_staff", campaign.notify_staff)
        campaign.is_active = self._bool_from_data("is_active", campaign.is_active)

        try:
            campaign.validate_configuration(field_defs=field_defs)
        except ValidationError as exc:
            if not hasattr(exc, "message_dict"):
                raise

            messages = []
            for field_name, field_errors in exc.message_dict.items():
                label = self.FIELD_LABELS.get(field_name, field_name)
                if not isinstance(field_errors, (list, tuple)):
                    field_errors = [field_errors]
                messages.extend(f"{label}: {error}" for error in field_errors)
            raise ValidationError(messages)


class RegistrationFieldInline(StackedInline, TranslationStackedInline):
    model = RegistrationField
    formset = RegistrationFieldInlineFormSet
    ordering_field = "sort_order"
    hide_ordering_field = True
    extra = 0
    ordering = ("sort_order", "id")
    fields = ("sort_order", "key", "label", "field_type", "choices_text", "required")


@admin.register(RegistrationEmailSender)
class RegistrationEmailSenderAdmin(BaseModelAdmin):
    list_display = ("title", "email", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("title", "email")
    readonly_fields = ("created_at",)

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser and super().has_view_permission(request, obj)

    def has_add_permission(self, request):
        return request.user.is_superuser and super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser and super().has_delete_permission(request, obj)


@admin.register(RegistrationCampaign)
class RegistrationCampaignAdmin(BaseModelAdmin, TabbedTranslationAdmin):
    formfield_overrides = {
        models.TextField: {
            "widget": WysiwygWidget,
        }
    }
    compressed_fields = True
    list_display = ("title", "slug", "owner", "is_active", "sort_order", "public_form_url", "created_at")
    list_filter = ("is_active",)
    search_fields = ("title", "slug", "subtitle", "owner__username", "owner__email")
    inlines = [RegistrationFieldInline]

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        for field_name in form.base_fields:
            if field_name == "staff_notification_emails":
                form.base_fields[field_name].widget = forms.Textarea(attrs={"rows": 4, "cols": 80})
            if (
                field_name == "participation_terms"
                or field_name.startswith("participation_terms_")
                or field_name == "applicant_email_body"
                or field_name.startswith("applicant_email_body_")
                or field_name == "ticket_footer_note"
                or field_name.startswith("ticket_footer_note_")
            ):  
                form.base_fields[field_name].widget = WysiwygWidget()
            if field_name == "sender_address":
                sender_qs = RegistrationEmailSender.objects.filter(is_active=True)
                if obj and obj.sender_address_id:
                    sender_qs = RegistrationEmailSender.objects.filter(Q(is_active=True) | Q(pk=obj.sender_address_id))
                form.base_fields[field_name].queryset = sender_qs
        for name in (
            "applicant_email_body",
            "staff_email_body",
            "success_message",
            "participation_terms",
            "ticket_footer_note",
        ):
            if name in form.base_fields:
                form.base_fields[name].widget.attrs.setdefault("rows", 16)
                form.base_fields[name].widget.attrs.setdefault("cols", 80)
        return form

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(owner=request.user)

    def has_view_permission(self, request, obj=None):
        allowed = super().has_view_permission(request, obj)
        if not allowed or request.user.is_superuser or obj is None:
            return allowed
        return obj.owner_id == request.user.id

    def has_change_permission(self, request, obj=None):
        allowed = super().has_change_permission(request, obj)
        if not allowed or request.user.is_superuser or obj is None:
            return allowed
        return obj.owner_id == request.user.id

    def has_delete_permission(self, request, obj=None):
        allowed = super().has_delete_permission(request, obj)
        if not allowed or request.user.is_superuser or obj is None:
            return allowed
        return obj.owner_id == request.user.id

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        ro.extend(["created_at", "updated_at", "public_form_url", "email_template_guide"])
        if not request.user.is_superuser:
            ro.append("owner")
        return ro

    def get_fields(self, request, obj=None):
        fields = list(super().get_fields(request, obj))
        if not request.user.is_superuser and "owner" in fields:
            fields.remove("owner")
        if "public_form_url" not in fields:
            fields.append("public_form_url")
        return fields

    def save_model(self, request, obj, form, change):
        if not obj.owner_id:
            obj.owner = request.user
        elif not request.user.is_superuser and obj.owner_id != request.user.id:
            obj.owner = request.user
        super().save_model(request, obj, form, change)

    @admin.display(description=_("Публичная ссылка"))
    def public_form_url(self, obj):
        if not obj or not obj.slug:
            return "—"
        path = reverse("registration_form", args=[obj.slug])
        return format_html('<a href="{}" target="_blank" rel="noopener">{}</a>', path, path)

    @admin.display(description=_("Инструкция по шаблонам письма"))
    def email_template_guide(self, obj):
        placeholders = [
            ("{ключ_поля}", _("Значение конкретного поля формы, например: {first_name}, {contact_email}.")),
            ("{applicant_name}", _("Собранное ФИО/имя по настройке «Ключи ФИО через запятую».")),
            ("{applicant_email}", _("Email заявителя из поля «Ключ поля с email заявителя».")),
            ("{campaign_title}", _("Название формы/кампании.")),
            ("{campaign_subtitle}", _("Подзаголовок формы.")),
            ("{campaign_slug}", _("Код формы в URL.")),
            ("{submission_id}", _("ID заявки.")),
            ("{all_fields}", _("Все заполненные поля заявки списком.")),
            ("{ticket_url}", _("Ссылка на страницу электронного билета.")),
            ("{ticket_pdf_url}", _("Ссылка на PDF-версию билета.")),
            ("{ticket_code}", _("Код билета для проверки/сканирования.")),
            ("{campaign_event_dates}", _("Даты проведения мероприятия.")),
            ("{campaign_event_schedule}", _("Время работы мероприятия.")),
            ("{campaign_event_location}", _("Место проведения мероприятия.")),
            ("{campaign_event_contact}", _("Контакты оргкомитета.")),
        ]
        rows = format_html_join("", "<li><code>{}</code> — {}</li>", ((k, v) for k, v in placeholders))
        return format_html(
            "<div style='max-width: 980px'>"
            "<p><strong>{}</strong></p>"
            "<p>{}</p>"
            "<ul style='margin: 0 0 12px 18px'>{}</ul>"
            "<p><strong>{}</strong></p>"
            "<pre style='white-space: pre-wrap; margin: 0; background: #f8fafc; border: 1px solid #e2e8f0; padding: 10px; border-radius: 6px'>"
            "Здравствуйте, {{first_name}}!\n"
            "Ваша заявка №{{submission_id}} принята.\n"
            "Ваш билет: {{ticket_url}}"
            "</pre>"
            "</div>",
            _("Как работают подстановки"),
            _("Эти переменные можно использовать в теме и тексте письма. При отправке они заменяются на реальные данные заявки."),
            rows,
            _("Пример шаблона"),
        )

    fieldsets = (
        (None, {"fields": ("owner", "title", "slug", "subtitle", "is_active", "sort_order", "public_form_url")}),
        (
            _("Данные заявителя и дубликаты"),
            {
                "fields": (
                    "allow_duplicate_submissions",
                    "applicant_email_field_key",
                    "applicant_name_field_keys",
                ),
            },
        ),
        (
            _("Письмо заявителю"),
            {
                "fields": (
                    "send_applicant_confirmation",
                    "sender_address",
                    "applicant_email_subject",
                    "applicant_email_body",
                    "email_template_guide",
                ),
            },
        ),
        (
            _("Письма организаторам"),
            {
                "fields": (
                    "notify_staff",
                    "staff_notification_emails",
                    "staff_email_subject",
                    "staff_email_body",
                ),
            },
        ),
        (_("Страница благодарности"), {"fields": ("success_message",)}),
        (_("Условия участия"), {"fields": ("participation_terms",)}),
        (
            _("Общие поля билета"),
            {
                "fields": (
                    "ticket_participant_label",
                    "event_dates",
                    "event_schedule",
                    "event_location",
                    "event_contact",
                    "ticket_footer_note",
                )
            },
        ),
        (
            _("Электронный билет"),
            {
                "fields": (
                    "ticket_heading",
                    "ticket_subtitle",
                    "ticket_pdf_field_keys",
                )
            },
        ),
        (
            _("Печатный билет"),
            {
                "fields": (
                    "ticket_print_heading",
                    "ticket_print_field_keys",
                )
            },
        ),
        (_("Служебное"), {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(RegistrationSubmission)
class RegistrationSubmissionAdmin(BaseModelAdmin):
    list_display = ("campaign", "applicant_name", "applicant_email", "ticket_link", "resend_email_button", "created_at")
    list_filter = ("campaign",)
    search_fields = ("applicant_name", "applicant_email")
    readonly_fields = (
        "campaign",
        "applicant_email",
        "applicant_name",
        "ticket_token",
        "ticket_link",
        "resend_email_button",
        "created_at",
    )
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "campaign",
                    "applicant_name",
                    "applicant_email",
                    "created_at",
                    "ticket_link",
                    "resend_email_button",
                    "ticket_token",
                    'language_code'
                )
            },
        ),
        (_("Данные"), {"fields": ("data",)}),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<path:object_id>/resend-email/",
                self.admin_site.admin_view(self.resend_email_view),
                name="account_registrationsubmission_resend_email",
            ),
        ]
        return custom_urls + urls

    @admin.display(description=_("Билет"))
    def ticket_link(self, obj):
        if not obj or not obj.ticket_token:
            return "—"
        path = reverse("exhibition_ticket", args=[obj.ticket_token])
        return format_html('<a href="{}" target="_blank" rel="noopener">{}</a>', path, _("Открыть"))

    @admin.display(description=_("Отправка письма"))
    def resend_email_button(self, obj):
        if not obj or not obj.pk:
            return "—"
        url = reverse("admin:account_registrationsubmission_resend_email", args=[obj.pk])
        return format_html('<a class="button" href="{}">{}</a>', url, _("Отправить снова"))

    def save_model(self, request, obj, form, change):
        obj.apply_applicant_snapshot()
        super().save_model(request, obj, form, change)

    def resend_email_view(self, request, object_id):
        obj = self.get_object(request, object_id)
        if obj is None:
            self.message_user(request, _("Заявка не найдена."), level="error")
            return HttpResponseRedirect(reverse("admin:account_registrationsubmission_changelist"))

        if not self.has_view_permission(request, obj):
            self.message_user(request, _("Недостаточно прав для отправки письма по этой заявке."), level="error")
            return HttpResponseRedirect(reverse("admin:account_registrationsubmission_changelist"))

        try:
            queue_registration_submission_emails(obj.pk)
            self.message_user(request, _("Письмо отправлено повторно."))
        except Exception:
            self.message_user(request, _("Не удалось отправить письмо повторно."), level="error")

        return HttpResponseRedirect(reverse("admin:account_registrationsubmission_change", args=[obj.pk]))

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(campaign__owner=request.user)

    def has_view_permission(self, request, obj=None):
        allowed = super().has_view_permission(request, obj)
        if not allowed or request.user.is_superuser or obj is None:
            return allowed
        return obj.campaign.owner_id == request.user.id

    def has_add_permission(self, request):
        return False
