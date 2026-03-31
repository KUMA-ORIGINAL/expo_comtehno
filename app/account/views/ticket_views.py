import re

from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.html import strip_tags
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import override

from account.models.exhibition_visitor import ExhibitionVisitor
from account.models.registration import RegistrationField, RegistrationSubmission, parse_field_choices
from account.ticket_utils import (
    REPORTLAB_AVAILABLE,
    build_qr_data_uri,
    build_qr_image_reader,
    ensure_submission_ticket_token,
    ensure_visitor_ticket_token,
    get_pdf_font_name,
    submission_ticket_code,
    try_resolve_ticket_token,
    visitor_ticket_code,
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
    default_footer = _("Предъявите билет при регистрации на мероприятии (в электронном или печатном виде).")
    return {
        "heading": (campaign.ticket_heading or default_heading).strip(),
        "subtitle": (campaign.ticket_subtitle or "").strip(),
        "print_heading": (campaign.ticket_print_heading or campaign.ticket_heading or default_heading).strip(),
        "participant_label": (campaign.ticket_participant_label or default_participant_label).strip(),
        "footer_note": (
            campaign.ticket_footer_note
            or default_footer
        ).strip(),
    }


def _split_keys(value: str) -> list[str]:
    return [k.strip() for k in (value or "").split(",") if k.strip()]


def _submission_ticket_rows(submission: RegistrationSubmission, target: str) -> list[tuple[str, str]]:
    campaign = submission.campaign
    keys = _split_keys(campaign.ticket_print_field_keys if target == "print" else campaign.ticket_pdf_field_keys)
    if not keys:
        return []

    selected = set(keys)
    rows: list[tuple[str, str]] = []
    for fd in campaign.fields.all().order_by("sort_order", "id"):
        if fd.key not in selected:
            continue
        raw = submission.data.get(fd.key, "")
        if fd.field_type == RegistrationField.TYPE_RADIO:
            for val, lab in parse_field_choices(fd.choices_text):
                if str(raw) == val:
                    raw = lab
                    break
        rows.append((fd.label, str(raw or "—")))
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
    kind, obj = try_resolve_ticket_token(token)
    canonical = obj.ticket_token or token

    if kind == "visitor":
        visitor = obj
        if REPORTLAB_AVAILABLE:
            return redirect("exhibition_ticket_pdf", token=canonical)
        ticket_url = request.build_absolute_uri(reverse("exhibition_ticket", args=[canonical]))
        return render(
            request,
            "registration/exhibition_ticket.html",
            {
                "visitor": visitor,
                "submission": None,
                "ticket_token": canonical,
                "ticket_qr_data_uri": build_qr_data_uri(ticket_url),
            },
        )

    submission = obj
    with override((submission.language_code or "ru").split("-", 1)[0]):
        if REPORTLAB_AVAILABLE:
            return redirect("exhibition_ticket_pdf", token=canonical)
        ticket_url = request.build_absolute_uri(reverse("exhibition_ticket", args=[canonical]))
        return render(
            request,
            "registration/exhibition_ticket.html",
            {
                "visitor": None,
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

    kind, obj = try_resolve_ticket_token(token)
    canonical = obj.ticket_token or token
    response = HttpResponse(content_type="application/pdf")

    if kind == "visitor":
        visitor = obj
        response["Content-Disposition"] = f'inline; filename="icee-ticket-{visitor.id}.pdf"'
        _draw_visitor_pdf(request, response, visitor, canonical)
        return response

    submission = obj
    response["Content-Disposition"] = f'inline; filename="reg-ticket-{submission.id}.pdf"'
    with override((submission.language_code or "ru").split("-", 1)[0]):
        _draw_submission_pdf(request, response, submission, canonical)
    return response


def _draw_visitor_pdf(request, response, visitor, token):
    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    font_name = get_pdf_font_name()

    p.setFillColorRGB(0.11, 0.31, 0.85)
    p.rect(0, height - 36 * mm, width, 36 * mm, fill=1, stroke=0)
    p.setFillColorRGB(1, 1, 1)
    p.setFont(font_name, 24)
    p.drawString(20 * mm, height - 28 * mm, "ICEE 2026")
    p.setFont(font_name, 12)
    p.drawString(20 * mm, height - 36 * mm, _("ЭЛЕКТРОННЫЙ БИЛЕТ"))

    p.setFillColorRGB(0.12, 0.16, 0.23)
    p.setFont(font_name, 16)
    p.drawString(20 * mm, height - 70 * mm, _("Посетитель:"))
    p.setFont(font_name, 20)
    full_name = f"{visitor.last_name} {visitor.first_name} {visitor.middle_name or ''}".strip()
    p.drawString(20 * mm, height - 82 * mm, full_name)

    ticket_url = request.build_absolute_uri(reverse("exhibition_ticket", args=[token]))
    qr_reader = build_qr_image_reader(ticket_url)
    p.drawImage(qr_reader, width - 72 * mm, height - 136 * mm, 50 * mm, 50 * mm, mask="auto")

    p.setFont(font_name, 12)
    p.drawString(20 * mm, height - 100 * mm, f"{_('Компания')}: {visitor.company}")
    p.drawString(20 * mm, height - 108 * mm, f"{_('Email')}: {visitor.email}")
    local_created_at = timezone.localtime(visitor.created_at)
    p.drawString(20 * mm, height - 116 * mm, f"{_('Дата регистрации')}: {local_created_at.strftime('%d.%m.%Y %H:%M')}")

    p.setFont(font_name, 13)
    p.drawString(20 * mm, height - 136 * mm, _("Дата и время проведения:"))
    p.setFont(font_name, 12)
    p.drawString(20 * mm, height - 145 * mm, _("14-15 апреля: 10:00-18:00"))
    p.drawString(20 * mm, height - 152 * mm, _("16 апреля: 10:00-16:00"))
    p.drawString(20 * mm, height - 163 * mm, _("Адрес: г. Бишкек, ул. Ахунбаева, 97, Манеж КГАФКиС"))

    p.setStrokeColorRGB(0.75, 0.8, 0.9)
    p.line(20 * mm, height - 176 * mm, width - 20 * mm, height - 176 * mm)
    p.setFont(font_name, 10)
    p.setFillColorRGB(0.3, 0.35, 0.42)
    p.drawString(20 * mm, height - 184 * mm, _("Для входа предъявите билет в распечатанном или электронном виде."))
    p.drawString(20 * mm, height - 191 * mm, _("Контакты: +996 775 000 005, info@icee.kg"))

    p.showPage()
    p.save()

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags


def _draw_submission_pdf(request, response, submission, token):
    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    font_name = get_pdf_font_name()
    c = submission.campaign
    ui = _submission_ticket_ui(c)

    # ---------- Colors ----------
    PRIMARY = colors.HexColor("#1D4ED8")
    PRIMARY_DARK = colors.HexColor("#1E3A8A")
    TEXT = colors.HexColor("#0F172A")
    MUTED = colors.HexColor("#475569")
    LIGHT_TEXT = colors.HexColor("#64748B")
    BORDER = colors.HexColor("#D7DEE8")
    BG = colors.HexColor("#F3F4F6")
    WHITE = colors.white

    # ---------- Background ----------
    p.setFillColor(BG)
    p.rect(0, 0, width, height, fill=1, stroke=0)

    # ---------- Header ----------
    header_h = 38 * mm
    p.setFillColor(PRIMARY)
    p.rect(0, height - header_h, width, header_h, fill=1, stroke=0)

    p.setFillColor(WHITE)
    p.setFont(font_name, 20)
    p.drawString(18 * mm, height - 15 * mm, (ui["heading"] or "")[:80])

    if ui.get("subtitle"):
        p.setFont(font_name, 12)
        for i, line in enumerate(_wrap_reportlab_text(p, ui["subtitle"], width - 36 * mm, font_name, 12)[:2]):
            p.drawString(18 * mm, height - (22 + i * 5) * mm, line)

    # ---------- Main card ----------
    card_x = 15 * mm
    card_y = 18 * mm
    card_w = width - 30 * mm
    card_h = height - header_h - 28 * mm

    p.setFillColor(WHITE)
    p.setStrokeColor(BORDER)
    p.roundRect(card_x, card_y, card_w, card_h, 6 * mm, fill=1, stroke=1)

    inner_pad = 12 * mm
    content_x = card_x + inner_pad
    content_top = card_y + card_h - inner_pad

    # ---------- Participant label ----------
    p.setFillColor(PRIMARY_DARK)
    p.setFont(font_name, 13)
    p.drawString(content_x, content_top, ui["participant_label"])

    # ---------- Name ----------
    name = (submission.applicant_name or "—")[:120]
    p.setFillColor(TEXT)
    p.setFont(font_name, 24)
    name_y = content_top - 10 * mm

    name_lines = _wrap_reportlab_text(p, name, card_w - 100 * mm, font_name, 24)[:2]
    for line in name_lines:
        p.drawString(content_x, name_y, line)
        name_y -= 8 * mm

    # ---------- QR block ----------
    qr_size = 50 * mm
    qr_pad = 4 * mm

    qr_x = card_x + card_w - inner_pad - qr_size - 6 * mm
    qr_y = content_top - 58 * mm

    qr_box_x = qr_x - qr_pad
    qr_box_y = qr_y - qr_pad
    qr_box_w = qr_size + qr_pad * 2
    qr_box_h = qr_size + qr_pad * 2

    p.setFillColor(colors.HexColor("#F8FAFC"))
    p.setStrokeColor(BORDER)
    p.roundRect(
        qr_box_x,
        qr_box_y,
        qr_box_w,
        qr_box_h,
        5 * mm,
        fill=1,
        stroke=1,
    )

    ticket_url = request.build_absolute_uri(reverse("exhibition_ticket", args=[token]))
    qr_reader = build_qr_image_reader(ticket_url)
    p.drawImage(qr_reader, qr_x, qr_y, qr_size, qr_size, mask="auto")

    # ---------- Left column widths ----------
    left_w = qr_x - content_x - 18 * mm

    def draw_block(label, value, y_pos, label_size=12, value_size=14, gap=8 * mm):
        if not value:
            return y_pos

        p.setFillColor(MUTED)
        p.setFont(font_name, label_size)
        for line in _wrap_reportlab_text(p, label, left_w, font_name, label_size):
            p.drawString(content_x, y_pos, line)
            y_pos -= 5.2 * mm

        p.setFillColor(TEXT)
        p.setFont(font_name, value_size)
        for line in _wrap_reportlab_text(p, str(value), left_w, font_name, value_size):
            p.drawString(content_x, y_pos, line)
            y_pos -= 6.0 * mm

        y_pos -= gap - 6.0 * mm
        return y_pos

    # ---------- Upper info block ----------
    y = name_y - 2 * mm

    # ВОТ ЭТОТ КОД НИКУДА НЕ ДЕЛСЯ — оставляем дополнительные поля
    for label, value in _submission_ticket_rows(submission, target="pdf"):
        y = draw_block(label, value, y, label_size=12, value_size=13, gap=6 * mm)
        if y < card_y + 90 * mm:
            break

    if submission.applicant_email:
        y -= 10 * mm
        y = draw_block(_("Email"), submission.applicant_email, y, label_size=12, value_size=13, gap=7 * mm)

    local_created_at = timezone.localtime(submission.created_at)
    y = draw_block(
        _("Дата регистрации"),
        local_created_at.strftime("%d.%m.%Y %H:%M"),
        y,
        label_size=12,
        value_size=13,
        gap=7 * mm,
    )

    # ---------- Event block BELOW ----------
    y = draw_block(
        _("Код"),
        submission_ticket_code(submission.id),
        y,
        label_size=12,
        value_size=13,
        gap=10 * mm,
    )
    event_block_y = y - 10 * mm

    if c.event_dates:
        event_block_y = draw_block(
            _("Даты проведения:"),
            c.event_dates,
            event_block_y,
            label_size=12,
            value_size=14,
            gap=9 * mm,
        )

    if c.event_schedule:
        event_block_y = draw_block(
            _("Время работы:"),
            c.event_schedule,
            event_block_y,
            label_size=12,
            value_size=14,
            gap=9 * mm,
        )

    if c.event_location:
        event_block_y = draw_block(
            _("Место проведения:"),
            c.event_location,
            event_block_y,
            label_size=12,
            value_size=14,
            gap=9 * mm,
        )

    # ---------- Footer (HTML, with top divider only) ----------
    footer_x = card_x + 10 * mm
    footer_w = card_w - 20 * mm

    footer_html = (ui.get("footer_note") or "").strip()
    footer_html = re.sub(r"(?i)</?div[^>]*>", "<br/>", footer_html)
    footer_html = re.sub(r"(?i)</?p[^>]*>", "<br/>", footer_html)
    footer_html = re.sub(r"(?i)<br\s*/?>", "<br/>", footer_html)
    footer_html = re.sub(r"(&nbsp;|\s)+", " ", footer_html)
    footer_html = re.sub(r"(<br/>\s*){3,}", "<br/><br/>", footer_html).strip()

    if not footer_html:
        footer_html = strip_tags(ui.get("footer_note") or "").strip()

    footer_style = ParagraphStyle(
        name="TicketFooter",
        fontName=font_name,
        fontSize=11,
        leading=13,
        textColor=colors.HexColor("#334155"),
        spaceBefore=0,
        spaceAfter=0,
        allowWidows=1,
        allowOrphans=1,
    )

    footer_par = Paragraph(footer_html, footer_style)

    footer_top_pad = 4 * mm
    footer_bottom_pad = 2 * mm
    footer_inner_pad_x = 0 * mm
    footer_gap_from_line = 3.5 * mm
    footer_line_offset = 2 * mm 

    available_text_w = footer_w - (footer_inner_pad_x * 2)
    _w, need_h = footer_par.wrap(available_text_w, 200 * mm)

    footer_h = footer_top_pad + footer_gap_from_line + need_h + footer_bottom_pad

    footer_bottom_margin = 8 * mm
    footer_y = card_y + footer_bottom_margin
    footer_top = footer_y + footer_h

    line_y = footer_top - footer_line_offset

    p.setStrokeColor(colors.HexColor("#CBD5E1"))
    p.setLineWidth(0.8)
    p.line(footer_x, line_y, footer_x + footer_w, line_y)

    text_x = footer_x + footer_inner_pad_x
    text_y = line_y - footer_gap_from_line - need_h
    footer_par.drawOn(p, text_x, text_y)

    p.showPage()
    p.save()


def exhibition_ticket_print(request, token):
    kind, obj = try_resolve_ticket_token(token)
    canonical = obj.ticket_token or token
    ticket_url = request.build_absolute_uri(reverse("exhibition_ticket", args=[canonical]))
    if kind == "submission":
        submission = obj
        with override((submission.language_code or "ru").split("-", 1)[0]):
            ctx = {
                "visitor": None,
                "submission": submission,
                "ticket_kind": kind,
                "ticket_code": submission_ticket_code(submission.id),
                "ticket_qr_data_uri": build_qr_data_uri(ticket_url),
                "ticket_token": canonical,
                "submission_ticket_ui": _submission_ticket_ui(submission.campaign),
                "ticket_print_rows": _submission_ticket_rows(submission, target="print"),
            }
            return render(request, "registration/exhibition_ticket_print.html", ctx)

    ctx = {
        "visitor": obj,
        "submission": None,
        "ticket_kind": kind,
        "ticket_code": visitor_ticket_code(obj.id),
        "ticket_qr_data_uri": build_qr_data_uri(ticket_url),
        "ticket_token": canonical,
    }
    return render(request, "registration/exhibition_ticket_print.html", ctx)


def _resolve_scan(raw_value):
    value = (raw_value or "").strip()
    if not value:
        raise Http404(_("Пустой код билета."))

    if "/ticket/" in value:
        match = re.search(r"/ticket/([^/]+)/?", value)
        if match:
            token = match.group(1)
            kind, obj = try_resolve_ticket_token(token)
            return kind, obj, obj.ticket_token or token

    if value.upper().startswith("REG-"):
        num = value.split("-", 1)[1]
        if num.isdigit():
            sub = RegistrationSubmission.objects.filter(id=int(num)).select_related("campaign").first()
            if sub:
                tok = ensure_submission_ticket_token(sub)
                return "submission", sub, tok

    if value.upper().startswith("ICEE-"):
        ticket_number = value.split("-", 1)[1]
        if ticket_number.isdigit():
            visitor = ExhibitionVisitor.objects.filter(id=int(ticket_number)).first()
            if visitor:
                tok = ensure_visitor_ticket_token(visitor)
                return "visitor", visitor, tok

    if value.isdigit():
        visitor = ExhibitionVisitor.objects.filter(id=int(value)).first()
        if visitor:
            tok = ensure_visitor_ticket_token(visitor)
            return "visitor", visitor, tok
        sub = RegistrationSubmission.objects.filter(id=int(value)).select_related("campaign").first()
        if sub:
            tok = ensure_submission_ticket_token(sub)
            return "submission", sub, tok

    kind, obj = try_resolve_ticket_token(value)
    return kind, obj, obj.ticket_token or value


@staff_member_required
def exhibition_checkin(request):
    visitor = None
    submission = None
    token = None
    error = None
    scanned_value = ""
    if request.method == "POST":
        scanned_value = request.POST.get("ticket_code", "")
        try:
            kind, obj, token = _resolve_scan(scanned_value)
            if kind == "visitor":
                visitor = obj
            else:
                submission = obj
        except Http404 as exc:
            error = str(exc)
    return render(
        request,
        "registration/exhibition_checkin.html",
        {
            "visitor": visitor,
            "submission": submission,
            "ticket_token": token,
            "scanned_value": scanned_value,
            "error": error,
        },
    )
