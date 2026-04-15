import re
from email.utils import parseaddr

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import models
from django.utils.translation import gettext_lazy as _


def parse_field_choices(text: str) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for line in (text or "").strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if "|" in line:
            val, label = line.split("|", 1)
            result.append((val.strip(), label.strip()))
        else:
            result.append((line, line))
    return result


FIELD_KEY_RE = re.compile(r"^[a-z0-9_]+$")


class RegistrationEmailSender(models.Model):
    title = models.CharField(_("Название"), max_length=255)
    email = models.EmailField(_("Email отправителя"), unique=True)
    is_active = models.BooleanField(_("Активен"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Email отправителя")
        verbose_name_plural = _("Email отправителей")
        ordering = ["title", "email"]

    def __str__(self):
        return f"{self.title} <{self.email}>"


class RegistrationCampaign(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="registration_campaigns",
        verbose_name=_("Владелец формы"),
        blank=True,
        null=True,
        help_text=_("Сотрудник, который управляет этой формой в админке."),
    )
    slug = models.SlugField(
        _("Код в URL"),
        max_length=80,
        unique=True,
        db_index=True,
        help_text=_("Латиница и цифры, например: ucastie-2026. Адрес формы: /r/этот-код/"),
    )
    title = models.CharField(_("Заголовок формы"), max_length=255)
    subtitle = models.CharField(_("Подзаголовок"), max_length=500, blank=True)
    is_active = models.BooleanField(_("Форма открыта"), default=True)
    sort_order = models.PositiveSmallIntegerField(_("Порядок в списке"), default=0)

    allow_duplicate_submissions = models.BooleanField(
        _("Разрешить повторные заявки с тем же email"),
        default=False,
    )
    applicant_email_field_key = models.SlugField(
        _("Ключ поля с email заявителя"),
        max_length=64,
        default="contact_email",
        help_text=_("Для проверки дубликатов и отправки копии заявителю."),
    )
    applicant_name_field_keys = models.CharField(
        _("Ключи ФИО через запятую"),
        max_length=200,
        default="last_name,first_name,middle_name",
        help_text=_("Например: last_name,first_name,middle_name"),
    )

    send_applicant_confirmation = models.BooleanField(_("Отправить письмо заявителю"), default=True)
    sender_email = models.EmailField(
        _("Email отправителя"),
        blank=True,
        help_text=_("Если пусто, используется DEFAULT_FROM_EMAIL из настроек проекта."),
    )
    sender_address = models.ForeignKey(
        RegistrationEmailSender,
        on_delete=models.SET_NULL,
        related_name="campaigns",
        verbose_name=_("Email отправителя"),
        blank=True,
        null=True,
        help_text=_("Если не выбран, используется DEFAULT_FROM_EMAIL из настроек проекта."),
    )
    applicant_email_subject = models.CharField(_("Тема письма заявителю"), max_length=255, blank=True)
    applicant_email_body = models.TextField(
        _("Текст письма заявителю (plain text)"),
        blank=True,
        help_text=_(
            "Текст письма (plain text) и красивая HTML-версия с той же информацией и таблицей полей "
            "формируются автоматически. Подстановки: {ключ_поля}; {applicant_name}, {applicant_email}; "
            "{campaign_title}, {campaign_subtitle}, {campaign_slug}, {submission_id}; "
            "{campaign_event_dates}, {campaign_event_schedule}, {campaign_event_location}, {campaign_event_contact}; "
            "{ticket_url}, {ticket_pdf_url}, {ticket_code}; {all_fields}."
        ),
    )

    notify_staff = models.BooleanField(_("Уведомить организаторов по email"), default=True)
    staff_notification_emails = models.TextField(
        _("Email организаторов (по одному в строке)"),
        blank=True,
    )
    staff_email_subject = models.CharField(_("Тема письма организаторам"), max_length=255, blank=True)
    staff_email_body = models.TextField(
        _("Текст письма организаторам (plain text)"),
        blank=True,
        help_text=_(
            "Если заполнено — уходит этот текст (с подстановками). Если пусто — автоматическая сводка полей и ссылка на билет. "
            "Те же плейсхолдеры, что и у письма заявителю: {all_fields}, {ticket_pdf_url}, поля формы {ключ}, и т.д."
        ),
    )

    success_message = models.TextField(
        _("Текст на странице «Спасибо»"),
        blank=True,
        help_text=_("Если пусто — показывается стандартное сообщение."),
    )
    participation_terms = models.TextField(
        _("Условия участия"),
        blank=True,
        help_text=_("Показываются под формой регистрации."),
    )
    event_dates = models.CharField(
        _("Даты проведения"),
        max_length=255,
        blank=True,
    )
    event_schedule = models.CharField(
        _("Время работы"),
        max_length=255,
        blank=True,
    )
    event_location = models.CharField(
        _("Место проведения"),
        max_length=500,
        blank=True,
    )
    event_contact = models.CharField(
        _("Контакты оргкомитета"),
        max_length=255,
        blank=True,
        help_text=_("Например: +996 775 000 005 · info@icee.kg"),
    )
    ticket_heading = models.CharField(
        _("Заголовок подтверждения / билета"),
        max_length=255,
        blank=True,
        default="",
    )
    ticket_subtitle = models.CharField(
        _("Подзаголовок электронного билета"),
        max_length=255,
        blank=True,
        default="",
    )
    ticket_print_heading = models.CharField(
        _("Заголовок печатного билета"),
        max_length=255,
        blank=True,
        default="",
    )
    ticket_participant_label = models.CharField(
        _("Подпись перед ФИО участника"),
        max_length=255,
        blank=True,
        default="",
    )
    ticket_footer_note = models.TextField(
        _("Текст внизу билета"),
        blank=True,
        help_text=_("Короткая памятка, которая выводится внизу страницы/билета."),
    )

    ticket_pdf_field_keys = models.CharField(
        _("Ключи полей для PDF-билета"),
        max_length=500,
        blank=True,
        default="",
        help_text=_("Через запятую: например first_name,last_name,company."),
    )
    ticket_print_field_keys = models.CharField(
        _("Ключи полей для печатного билета"),
        max_length=500,
        blank=True,
        default="",
        help_text=_("Через запятую: например first_name,last_name,company."),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Регистрация / форма заявки")
        verbose_name_plural = _("Регистрации и формы")
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.title

    def applicant_name_keys_list(self) -> list[str]:
        return [k.strip() for k in (self.applicant_name_field_keys or "").split(",") if k.strip()]

    def validate_configuration(self, field_defs=None):
        errors = {}

        invalid_recipients = []
        for line in (self.staff_notification_emails or "").splitlines():
            raw = line.strip()
            if not raw:
                continue
            _display_name, parsed = parseaddr(raw)
            candidate = (parsed or raw).strip()
            try:
                validate_email(candidate)
            except ValidationError:
                invalid_recipients.append(raw)
        if invalid_recipients:
            errors["staff_notification_emails"] = _(
                "Некорректные email-адреса: {emails}"
            ).format(emails=", ".join(invalid_recipients))

        if field_defs is None:
            field_defs = [] if not self.pk else list(self.fields.all())

        if not field_defs:
            if self.is_active:
                errors["is_active"] = _("Для активной формы добавьте хотя бы одно поле.")
            if errors:
                raise ValidationError(errors)
            return

        field_map = {}
        duplicate_keys = set()
        for fd in field_defs:
            key = (getattr(fd, "key", "") or "").strip()
            if not key:
                continue
            if key in field_map:
                duplicate_keys.add(key)
                continue
            field_map[key] = fd

        if duplicate_keys:
            errors["__all__"] = _(
                "Ключи полей должны быть уникальны: {keys}"
            ).format(keys=", ".join(sorted(duplicate_keys)))

        requires_email_field = self.send_applicant_confirmation or not self.allow_duplicate_submissions
        email_key = (self.applicant_email_field_key or "").strip()
        email_field = field_map.get(email_key) if email_key else None
        if not email_key and requires_email_field:
            errors["applicant_email_field_key"] = _("Укажите ключ поля с email заявителя.")
        elif email_key and email_field is None and requires_email_field:
            errors["applicant_email_field_key"] = _(
                "Поле с ключом '{key}' не найдено среди полей формы."
            ).format(key=email_key)
        elif email_field is not None and getattr(email_field, "field_type", None) != RegistrationField.TYPE_EMAIL:
            errors["applicant_email_field_key"] = _(
                "Поле '{key}' должно иметь тип Email."
            ).format(key=email_key)

        name_keys = self.applicant_name_keys_list()
        if not name_keys:
            errors["applicant_name_field_keys"] = _("Укажите хотя бы один ключ поля для имени заявителя.")
        else:
            missing_name_keys = [key for key in name_keys if key not in field_map]
            if missing_name_keys:
                errors["applicant_name_field_keys"] = _(
                    "Поля для имени не найдены: {keys}"
                ).format(keys=", ".join(missing_name_keys))

        for cfg_key, cfg_label in (
            ("ticket_pdf_field_keys", _("Поля для PDF-билета")),
            ("ticket_print_field_keys", _("Поля для печатного билета")),
        ):
            configured_keys = [k.strip() for k in (getattr(self, cfg_key, "") or "").split(",") if k.strip()]
            missing = [k for k in configured_keys if k not in field_map]
            if missing:
                errors[cfg_key] = _("{label}: не найдены ключи {keys}").format(
                    label=cfg_label,
                    keys=", ".join(missing),
                )

        if errors:
            raise ValidationError(errors)

    def clean(self):
        super().clean()
        self.validate_configuration()


class RegistrationField(models.Model):
    TYPE_TEXT = "text"
    TYPE_TEXTAREA = "textarea"
    TYPE_EMAIL = "email"
    TYPE_PHONE = "phone"
    TYPE_RADIO = "radio"

    FIELD_TYPES = [
        (TYPE_TEXT, _("Одна строка")),
        (TYPE_TEXTAREA, _("Многострочный текст")),
        (TYPE_EMAIL, _("Email")),
        (TYPE_PHONE, _("Телефон")),
        (TYPE_RADIO, _("Один вариант из списка")),
    ]

    campaign = models.ForeignKey(
        RegistrationCampaign,
        on_delete=models.CASCADE,
        related_name="fields",
        verbose_name=_("Форма"),
    )
    key = models.SlugField(_("Ключ поля (латиница, _)"), max_length=64)
    label = models.CharField(_("Подпись"), max_length=255)
    field_type = models.CharField(_("Тип"), max_length=20, choices=FIELD_TYPES)
    choices_text = models.TextField(
        _("Варианты (для списка)"),
        blank=True,
        help_text=_("Каждая строка: значение|Подпись, например: in_person|Очная"),
    )
    required = models.BooleanField(_("Обязательное"), default=True)
    sort_order = models.PositiveIntegerField(_("Порядок"), default=0, db_index=True)

    class Meta:
        verbose_name = _("Поле формы")
        verbose_name_plural = _("Поля формы")
        ordering = ["sort_order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["campaign", "key"], name="uniq_registration_field_per_campaign"),
        ]

    def __str__(self):
        return f"{self.label} ({self.key})"

    def clean(self):
        super().clean()
        if self.key and not FIELD_KEY_RE.match(self.key):
            raise ValidationError({"key": _("Допустимы только латинские буквы, цифры и знак подчёркивания.")})
        if self.field_type == self.TYPE_RADIO and not parse_field_choices(self.choices_text):
            raise ValidationError({"choices_text": _("Укажите хотя бы один вариант.")})


class RegistrationSubmission(models.Model):
    campaign = models.ForeignKey(
        RegistrationCampaign,
        on_delete=models.CASCADE,
        related_name="submissions",
        verbose_name=_("Форма"),
    )
    data = models.JSONField(_("Данные формы"), default=dict)
    applicant_email = models.EmailField(_("Email заявителя"), blank=True, db_index=True)
    applicant_name = models.CharField(_("ФИО / имя"), max_length=500, blank=True)
    ticket_token = models.CharField(_("Токен электронного билета"), max_length=255, blank=True, null=True, unique=True)
    language_code = models.CharField(_("Язык заявки"), max_length=10, default="ru")
    created_at = models.DateTimeField(_("Подано"), auto_now_add=True)

    class Meta:
        verbose_name = _("Заявка")
        verbose_name_plural = _("Заявки")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.campaign.slug} — {self.applicant_name or self.applicant_email or self.pk}"

    def apply_applicant_snapshot(self):
        c = self.campaign
        email_key = (c.applicant_email_field_key or "").strip()
        if email_key:
            raw = self.data.get(email_key)
            self.applicant_email = (str(raw).strip() if raw is not None else "")[:254]
        keys = [k.strip() for k in (c.applicant_name_field_keys or "").split(",") if k.strip()]
        parts = [str(self.data.get(k) or "").strip() for k in keys]
        self.applicant_name = " ".join(p for p in parts if p).strip()[:500]
