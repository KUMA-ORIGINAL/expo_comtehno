import logging
import re
from email.utils import parseaddr

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import escape, strip_tags
from django.utils.translation import gettext as _
from django.utils.translation import override

from account.models import RegistrationField, RegistrationSubmission, parse_field_choices
from account.ticket_utils import ensure_submission_ticket_token, submission_ticket_code

logger = logging.getLogger(__name__)


def _format_placeholders(template: str, data: dict) -> str:
    def repl(match: re.Match) -> str:
        return str(data.get(match.group(1), ""))

    return re.sub(r"\{(\w+)\}", repl, template or "")


def _prepare_email_body_variants(text: str) -> tuple[str, str]:
    source = (text or "").strip()
    if not source:
        return "", ""

    plain = strip_tags(source)
    plain = re.sub(r"\r\n?", "\n", plain).strip()

    if re.search(r"<[^>]+>", source):
        html = source
    else:
        html = escape(source).replace("\n", "<br>")

    return plain, html


def _humanize_submission_data(submission: RegistrationSubmission) -> dict:
    out = dict(submission.data or {})
    radio_fields = submission.campaign.fields.filter(field_type=RegistrationField.TYPE_RADIO)
    for rf in radio_fields:
        k = rf.key
        if k not in out:
            continue
        raw = out[k]
        for val, lab in parse_field_choices(rf.choices_text):
            if val == raw:
                out[k] = lab
                break
    return out


def _staff_body_lines(submission: RegistrationSubmission) -> str:
    """Многострочная сводка полей заявки (для писем и плейсхолдера {all_fields})."""
    lines = []
    for fd in submission.campaign.fields.all().order_by("sort_order", "id"):
        raw = submission.data.get(fd.key, "—")
        if fd.field_type == RegistrationField.TYPE_RADIO:
            for val, lab in parse_field_choices(fd.choices_text):
                if val == raw:
                    raw = lab
                    break
        lines.append(f"{fd.label}: {raw}")
    lines.append("")
    lines.append(_("ID заявки: {id}").format(id=submission.pk))
    lines.append(_("Форма: {title} ({slug})").format(title=submission.campaign.title, slug=submission.campaign.slug))
    return "\n".join(lines)


def _email_placeholder_context(
    submission: RegistrationSubmission,
    display_data: dict,
    ticket_urls: dict,
) -> dict:
    campaign = submission.campaign
    all_fields = _staff_body_lines(submission)
    ctx = {
        **display_data,
        "applicant_name": submission.applicant_name or "",
        "applicant_email": submission.applicant_email or "",
        "campaign_title": campaign.title or "",
        "campaign_subtitle": campaign.subtitle or "",
        "campaign_slug": campaign.slug or "",
        "campaign_event_dates": campaign.event_dates or "",
        "campaign_event_schedule": campaign.event_schedule or "",
        "campaign_event_location": campaign.event_location or "",
        "campaign_event_contact": campaign.event_contact or "",
        "campaign_terms": campaign.participation_terms or "",
        "submission_id": str(submission.pk),
        "all_fields": all_fields,
        "ticket_url": ticket_urls["ticket_url"],
        "ticket_pdf_url": ticket_urls["ticket_pdf_url"],
        "ticket_code": ticket_urls["ticket_code"],
    }
    return ctx


def _field_rows_for_email(submission: RegistrationSubmission) -> list[dict]:
    rows = []
    for fd in submission.campaign.fields.all().order_by("sort_order", "id"):
        raw = submission.data.get(fd.key, "—")
        if fd.field_type == RegistrationField.TYPE_RADIO:
            for val, lab in parse_field_choices(fd.choices_text):
                if val == raw:
                    raw = lab
                    break
        rows.append({"label": fd.label, "value": str(raw)})
    return rows


def _parse_recipient_list(raw: str) -> list[str]:
    out = []
    for line in (raw or "").splitlines():
        addr = line.strip()
        if not addr:
            continue
        _, email = parseaddr(addr)
        target = email or addr
        if "@" in target:
            out.append(target)
    return out


def deliver_registration_submission_emails(submission_id: int) -> None:
    """Синхронная отправка писем по заявке (заявитель + организаторы)."""
    try:
        submission = RegistrationSubmission.objects.select_related("campaign").get(pk=submission_id)
    except RegistrationSubmission.DoesNotExist:
        logger.warning("deliver_registration_submission_emails: submission %s not found", submission_id)
        return

    campaign = submission.campaign
    lang = (submission.language_code or "ru").split("-", 1)[0]

    with override(lang):
        display_data = _humanize_submission_data(submission)
        ticket_tok = ensure_submission_ticket_token(submission)
        base = (settings.SITE_URL or "").rstrip("/")
        ticket_urls = {
            "ticket_url": f"{base}{reverse('exhibition_ticket', args=[ticket_tok])}",
            "ticket_pdf_url": f"{base}{reverse('exhibition_ticket_pdf', args=[ticket_tok])}",
            "ticket_code": submission_ticket_code(submission.id),
        }
        mail_ctx = _email_placeholder_context(submission, display_data, ticket_urls)
        field_rows = _field_rows_for_email(submission)

        if campaign.send_applicant_confirmation:
            to = (submission.applicant_email or "").strip()
            if to:
                default_subj = _("Заявка получена")
                subject_tpl = (campaign.applicant_email_subject or "").strip() or default_subj
                subject = _format_placeholders(subject_tpl, mail_ctx).strip() or default_subj
                body = _format_placeholders(campaign.applicant_email_body, mail_ctx)
                if not body.strip():
                    body = _("Спасибо, ваша заявка принята. При необходимости мы свяжемся с вами.")
                plain_body, html_body_content = _prepare_email_body_variants(body)
                try:
                    html_body = render_to_string(
                        "emails/submission_applicant.html",
                        {
                            "campaign": campaign,
                            "applicant_name": submission.applicant_name or "",
                            "body_plain": plain_body,
                            "body_html": html_body_content,
                            "field_rows": field_rows,
                            "ticket_url": mail_ctx["ticket_url"],
                            "ticket_pdf_url": mail_ctx["ticket_pdf_url"],
                            "ticket_code": mail_ctx["ticket_code"],
                        },
                    )
                    msg = EmailMultiAlternatives(
                        subject=subject,
                        body=plain_body,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        to=[to],
                    )
                    msg.attach_alternative(html_body, "text/html")
                    msg.send(fail_silently=False)
                except Exception:
                    logger.exception("Applicant email failed for submission %s", submission_id)
                    raise

        if campaign.notify_staff:
            recipients = _parse_recipient_list(campaign.staff_notification_emails)
            if recipients:
                default_staff_subj = _("Новая заявка: {title}").format(title=campaign.title)
                subject_tpl = (campaign.staff_email_subject or "").strip() or default_staff_subj
                subject = _format_placeholders(subject_tpl, mail_ctx).strip() or default_staff_subj
                staff_tpl = (campaign.staff_email_body or "").strip()
                staff_use_table = not bool(staff_tpl)
                if staff_tpl:
                    staff_body = _format_placeholders(staff_tpl, mail_ctx)
                else:
                    staff_body = (
                        mail_ctx["all_fields"]
                        + _("\n\nБилет (PDF): {url}\nКод: {code}").format(
                            url=mail_ctx["ticket_pdf_url"],
                            code=mail_ctx["ticket_code"],
                        )
                    )
                try:
                    html_staff = render_to_string(
                        "emails/submission_staff.html",
                        {
                            "campaign": campaign,
                            "submission_id": mail_ctx["submission_id"],
                            "field_rows": field_rows,
                            "staff_body": staff_body,
                            "staff_use_table": staff_use_table,
                            "ticket_url": mail_ctx["ticket_url"],
                            "ticket_pdf_url": mail_ctx["ticket_pdf_url"],
                            "ticket_code": mail_ctx["ticket_code"],
                        },
                    )
                    msg = EmailMultiAlternatives(
                        subject=subject,
                        body=staff_body,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        to=recipients,
                    )
                    msg.attach_alternative(html_staff, "text/html")
                    msg.send(fail_silently=False)
                except Exception:
                    logger.exception("Staff email failed for submission %s", submission_id)
                    raise


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 5, "countdown": 60},
)
def send_registration_submission_emails(self, submission_id: int) -> None:
    try:
        deliver_registration_submission_emails(submission_id)
    except Exception as exc:
        raise self.retry(exc=exc)


def queue_registration_submission_emails(submission_id: int) -> None:
    """По умолчанию — сразу из веб-процесса; при REGISTRATION_EMAIL_VIA_CELERY — через worker."""
    try:
        if getattr(settings, "REGISTRATION_EMAIL_VIA_CELERY", False):
            send_registration_submission_emails.delay(submission_id)
        else:
            deliver_registration_submission_emails(submission_id)
    except Exception:
        logger.exception("Unable to queue registration emails for submission %s", submission_id)
