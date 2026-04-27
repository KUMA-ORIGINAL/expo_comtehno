import re

from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.translation import gettext as _
from django.utils.translation import override

from account.models.registration import RegistrationField, RegistrationSubmission, parse_field_choices
from account.ticket_utils import (
    REPORTLAB_AVAILABLE,
    build_qr_data_uri,
    build_qr_image_reader,
    ensure_submission_ticket_token,
    get_pdf_font_name,
    submission_ticket_code,
    try_resolve_ticket_token,
)

if REPORTLAB_AVAILABLE:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.platypus import Paragraph


def _submission_ticket_ui(campaign):
    default_heading = _("ЭЛЕКТРОННЫЙ БИЛЕТ / ПОДТВЕРЖДЕНИЕ")
    default_participant_label = _("Участник")
    default_footer = _("Предъявите билет при регистрации на мероприятии.")
    return {
        "heading": (campaign.ticket_heading or default_heading).strip(),
        "subtitle": (campaign.ticket_subtitle or "").strip(),
        "print_heading": (campaign.ticket_print_heading or campaign.ticket_heading or default_heading).strip(),
        "participant_label": (campaign.ticket_participant_label or default_participant_label).strip(),
        "footer_note": (campaign.ticket_footer_note or default_footer).strip(),
    }


def _split_keys(value: str) -> list[str]:
    return [key.strip() for key in (value or "").split(",") if key.strip()]


def _submission_ticket_rows(submission: RegistrationSubmission, target: str) -> list[tuple[str, str]]:
    campaign = submission.campaign
    keys = _split_keys(campaign.ticket_print_field_keys if target == "print" else campaign.ticket_pdf_field_keys)
    if not keys:
        return []

    selected = set(keys)
    rows: list[tuple[str, str]] = []
    for field in campaign.fields.all().order_by("sort_order", "id"):
        if field.key not in selected:
            continue
        value = submission.data.get(field.key, "")
        if field.field_type == RegistrationField.TYPE_RADIO:
            for choice_value, choice_label in parse_field_choices(field.choices_text):
                if str(value) == choice_value:
                    value = choice_label
                    break
        rows.append((field.label, str(value or "-")))
    return rows


def _wrap_reportlab_text(c, text: str, max_width: float, font_name: str, font_size: int) -> list[str]:
    words = (text or "").split()
    if not words:
        return []
    lines = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if c.stringWidth(candidate, font_name, font_size) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def exhibition_ticket(request, token):
    _, submission = try_resolve_ticket_token(token)
    canonical = submission.ticket_token or token

    with override((submission.language_code or "ru").split("-", 1)[0]):
        if REPORTLAB_AVAILABLE:
            return redirect("exhibition_ticket_pdf", token=canonical)
        ticket_url = request.build_absolute_uri(reverse("exhibition_ticket", args=[canonical]))
        return render(
            request,
            "registration/exhibition_ticket.html",
            {
                "submission": submission,
                "ticket_token": canonical,
                "ticket_qr_data_uri": build_qr_data_uri(ticket_url),
                "submission_ticket_ui": _submission_ticket_ui(submission.campaign),
                "ticket_pdf_rows": _submission_ticket_rows(submission, target="pdf"),
            },
        )


def exhibition_ticket_pdf(request, token):
    if not REPORTLAB_AVAILABLE:
        return redirect("exhibition_ticket", token=token)

    _, submission = try_resolve_ticket_token(token)
    canonical = submission.ticket_token or token
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="reg-ticket-{submission.id}.pdf"'
    with override((submission.language_code or "ru").split("-", 1)[0]):
        _draw_submission_pdf(request, response, submission, canonical)
    return response


def _draw_submission_pdf(request, response, submission, token):
    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    font_name = get_pdf_font_name()
    campaign = submission.campaign
    ui = _submission_ticket_ui(campaign)

    primary = colors.HexColor("#1D4ED8")
    primary_dark = colors.HexColor("#1E3A8A")
    text = colors.HexColor("#0F172A")
    muted = colors.HexColor("#475569")
    border = colors.HexColor("#D7DEE8")
    bg = colors.HexColor("#F3F4F6")

    p.setFillColor(bg)
    p.rect(0, 0, width, height, fill=1, stroke=0)

    header_h = 38 * mm
    p.setFillColor(primary)
    p.rect(0, height - header_h, width, header_h, fill=1, stroke=0)

    p.setFillColor(colors.white)
    p.setFont(font_name, 20)
    p.drawString(18 * mm, height - 15 * mm, ui["heading"][:80])

    if ui["subtitle"]:
        p.setFont(font_name, 12)
        for i, line in enumerate(_wrap_reportlab_text(p, ui["subtitle"], width - 36 * mm, font_name, 12)[:2]):
            p.drawString(18 * mm, height - (22 + i * 5) * mm, line)

    card_x = 15 * mm
    card_y = 18 * mm
    card_w = width - 30 * mm
    card_h = height - header_h - 28 * mm
    inner_pad = 12 * mm
    content_x = card_x + inner_pad
    content_top = card_y + card_h - inner_pad

    p.setFillColor(colors.white)
    p.setStrokeColor(border)
    p.roundRect(card_x, card_y, card_w, card_h, 6 * mm, fill=1, stroke=1)

    p.setFillColor(primary_dark)
    p.setFont(font_name, 13)
    p.drawString(content_x, content_top, ui["participant_label"])

    name = (submission.applicant_name or "-")[:120]
    p.setFillColor(text)
    p.setFont(font_name, 24)
    y = content_top - 10 * mm
    for line in _wrap_reportlab_text(p, name, card_w - 100 * mm, font_name, 24)[:2]:
        p.drawString(content_x, y, line)
        y -= 8 * mm

    qr_size = 50 * mm
    qr_x = card_x + card_w - inner_pad - qr_size - 6 * mm
    qr_y = content_top - 58 * mm
    ticket_url = request.build_absolute_uri(reverse("exhibition_ticket", args=[token]))
    p.drawImage(build_qr_image_reader(ticket_url), qr_x, qr_y, qr_size, qr_size, mask="auto")

    left_w = qr_x - content_x - 18 * mm

    def draw_block(label, value, y_pos, label_size=11, value_size=12, gap=6 * mm):
        if not value:
            return y_pos
        if label:
            p.setFillColor(muted)
            p.setFont(font_name, label_size)
            for line in _wrap_reportlab_text(p, label, left_w, font_name, label_size):
                p.drawString(content_x, y_pos, line)
                y_pos -= 5.2 * mm
        p.setFillColor(text)
        p.setFont(font_name, value_size)
        for line in _wrap_reportlab_text(p, str(value), left_w, font_name, value_size):
            p.drawString(content_x, y_pos, line)
            y_pos -= 6.0 * mm
        return y_pos - gap + 6.0 * mm

    y -= 2 * mm
    for label, value in _submission_ticket_rows(submission, target="pdf"):
        y = draw_block("", value, y, value_size=14, gap=8 * mm)
        if y < card_y + 90 * mm:
            break

    y = card_y + 132 * mm
    y = draw_block(_("Email"), submission.applicant_email, y)
    y = draw_block(_("Дата регистрации"), timezone.localtime(submission.created_at).strftime("%d.%m.%Y %H:%M"), y)
    y = draw_block(_("Код"), submission_ticket_code(submission.id), y, gap=8 * mm)

    if campaign.event_dates:
        y = draw_block(_("Даты проведения:"), campaign.event_dates, y)
    if campaign.event_schedule:
        y = draw_block(_("Время работы:"), campaign.event_schedule, y)
    if campaign.event_location:
        y = draw_block(_("Место проведения:"), campaign.event_location, y)

    footer_html = (ui["footer_note"] or "").strip()
    footer_html = re.sub(r"(?i)</?div[^>]*>", "<br/>", footer_html)
    footer_html = re.sub(r"(?i)</?p[^>]*>", "<br/>", footer_html)
    footer_html = re.sub(r"(?i)<br\s*/?>", "<br/>", footer_html)
    footer_html = re.sub(r"(&nbsp;|\s)+", " ", footer_html)
    footer_html = re.sub(r"(<br/>\s*){3,}", "<br/><br/>", footer_html).strip()
    footer_html = footer_html or strip_tags(ui["footer_note"]).strip()

    footer_style = ParagraphStyle(
        name="TicketFooter",
        fontName=font_name,
        fontSize=11,
        leading=13,
        textColor=colors.HexColor("#334155"),
        alignment=TA_CENTER,
    )
    footer_par = Paragraph(footer_html, footer_style)
    footer_w = card_w - 20 * mm
    footer_text_w, footer_text_h = footer_par.wrap(footer_w, 200 * mm)
    footer_x = card_x + 10 * mm
    footer_y = card_y + 8 * mm
    line_y = footer_y + footer_text_h + 4 * mm
    p.setStrokeColor(colors.HexColor("#CBD5E1"))
    p.setLineWidth(0.8)
    p.line(footer_x, line_y, footer_x + footer_w, line_y)
    footer_par.drawOn(p, footer_x, footer_y)

    p.showPage()
    p.save()


def exhibition_ticket_print(request, token):
    _, submission = try_resolve_ticket_token(token)
    canonical = submission.ticket_token or token
    ticket_url = request.build_absolute_uri(reverse("exhibition_ticket", args=[canonical]))
    with override((submission.language_code or "ru").split("-", 1)[0]):
        return render(
            request,
            "registration/exhibition_ticket_print.html",
            {
                "submission": submission,
                "ticket_kind": "submission",
                "ticket_code": submission_ticket_code(submission.id),
                "ticket_qr_data_uri": build_qr_data_uri(ticket_url),
                "ticket_token": canonical,
                "submission_ticket_ui": _submission_ticket_ui(submission.campaign),
                "ticket_print_rows": _submission_ticket_rows(submission, target="print"),
            },
        )


def _resolve_scan(raw_value):
    value = (raw_value or "").strip()
    if not value:
        raise Http404(_("Пустой код билета."))

    if "/ticket/" in value:
        match = re.search(r"/ticket/([^/]+)/?", value)
        if match:
            token = match.group(1)
            _, submission = try_resolve_ticket_token(token)
            return submission, submission.ticket_token or token

    if value.upper().startswith("REG-"):
        num = value.split("-", 1)[1]
        if num.isdigit():
            submission = RegistrationSubmission.objects.filter(id=int(num)).select_related("campaign").first()
            if submission:
                return submission, ensure_submission_ticket_token(submission)

    if value.isdigit():
        submission = RegistrationSubmission.objects.filter(id=int(value)).select_related("campaign").first()
        if submission:
            return submission, ensure_submission_ticket_token(submission)

    _, submission = try_resolve_ticket_token(value)
    return submission, submission.ticket_token or value


@staff_member_required
def exhibition_checkin(request):
    submission = None
    token = None
    error = None
    scanned_value = ""
    if request.method == "POST":
        scanned_value = request.POST.get("ticket_code", "")
        try:
            submission, token = _resolve_scan(scanned_value)
        except Http404 as exc:
            error = str(exc)
    return render(
        request,
        "registration/exhibition_checkin.html",
        {
            "submission": submission,
            "ticket_token": token,
            "scanned_value": scanned_value,
            "error": error,
        },
    )
