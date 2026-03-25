from django.core.mail import EmailMultiAlternatives
from django.core import signing
from django.core.signing import BadSignature, SignatureExpired
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect
from django.http import Http404, HttpResponse
from django.conf import settings
from django.contrib import messages
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.urls import reverse
import qrcode
import base64
import io
import re
import os
import logging

from account.forms import ExhibitionRegistrationForm, EmailStepForm
from account.models.exhibition_visitor import ExhibitionVisitor

logger = logging.getLogger(__name__)

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except ModuleNotFoundError:
    REPORTLAB_AVAILABLE = False


def exhibition_landing(request):
    """Главная страница выставки с информацией и условиями."""
    return render(request, "exhibition_landing.html")


def exhibition_register_email(request):
    """Шаг 1: ввод email перед регистрацией."""
    if request.method == "POST":
        form = EmailStepForm(request.POST)
        if form.is_valid():
            request.session["registration_email"] = form.cleaned_data["email"]
            return redirect("exhibition_register")
    else:
        form = EmailStepForm()

    return render(request, "registration/email_step.html", {"form": form})


def exhibition_register(request):
    """Шаг 2: полная форма регистрации (требует email в сессии)."""
    email = request.session.get("registration_email")
    if not email:
        return redirect("exhibition_register_email")

    if request.method == "POST":
        form = ExhibitionRegistrationForm(request.POST, initial={"email": email})
        if form.is_valid():
            visitor = form.save(commit=False)
            visitor.email = email  # Всегда из сессии
            visitor.save()
            ticket_token = _ensure_ticket_token(visitor)
            request.session["registration_ticket_token"] = ticket_token
            _send_registration_email(visitor, ticket_token)
            del request.session["registration_email"]
            messages.success(
                request,
                _("Регистрация успешно завершена! На Ваш email отправлено письмо с билетом."),
            )
            return redirect("exhibition_register_success")
    else:
        form = ExhibitionRegistrationForm(initial={"email": email})

    return render(request, "registration/exhibition_register.html", {"form": form})


def _send_registration_email(visitor, ticket_token):
    """Отправка письма с билетом после регистрации."""
    subject = _("ICEE 2026 — Ваш билет на выставку")
    text_message = _(
        "Здравствуйте, {name}!\n\n"
        "Спасибо за регистрацию на выставку ICEE 2026.\n"
        "Дата: 14–16 апреля 2026\n"
        "Место: г. Бишкек, Манеж КГАФКиС\n\n"
        "Предъявите это письмо на стойке регистрации для получения бейджа.\n\n"
        "До встречи на выставке!"
    ).format(name=f"{visitor.first_name} {visitor.last_name}")
    ticket_url = f"{settings.SITE_URL}{reverse('exhibition_ticket_pdf', args=[ticket_token])}"
    context = {
        "full_name": f"{visitor.first_name} {visitor.last_name}".strip() or _("Гость"),
        "exhibition_name": "ICEE 2026",
        "dates": _("14–16 апреля 2026"),
        "address": _("г. Бишкек, ул. Ахунбаева, 97, Манеж КГАФКиС"),
        "participants_url": "https://icee.kg/participants",
        "ticket_url": ticket_url,
        "ticket_code": _ticket_code(visitor.id),
        "phone": "+996 775 000 005",
        "email": "info@icee.kg",
    }
    html_message = render_to_string("emails/registration_ticket.html", context)
    fallback_message = strip_tags(html_message)

    try:
        email = EmailMultiAlternatives(
            subject=str(subject),
            body=text_message or fallback_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[visitor.email],
        )
        email.attach_alternative(html_message, "text/html")
        email.send(fail_silently=True)
    except Exception:
        logger.exception("Failed to send registration email to %s", visitor.email)


def exhibition_register_success(request):
    """Страница успешной регистрации."""
    ticket_token = request.session.get("registration_ticket_token")
    return render(
        request,
        "registration/exhibition_register_success.html",
        {"ticket_token": ticket_token},
    )


def _build_ticket_token(visitor_id):
    return signing.dumps({"visitor_id": visitor_id}, salt="icee-ticket")


def _ticket_code(visitor_id):
    return f"ICEE-{int(visitor_id):06d}"


def _build_qr_data_uri(value):
    img = qrcode.make(value)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _build_qr_image_reader(value):
    img = qrcode.make(value)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)


def _get_pdf_font_name():
    static_font = os.path.join(
        str(settings.BASE_DIR),
        "account",
        "static",
        "fonts",
        "Inter_18pt-Bold.ttf",
    )
    candidates = [
        ("InterBold18", static_font),
        ("ArialUnicode", "C:/Windows/Fonts/arial.ttf"),
        ("DejaVuSans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        ("LiberationSans", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        ("LiberationSans2", "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
    ]
    for font_name, font_path in candidates:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont(font_name, font_path))
                return font_name
            except Exception:
                continue
    return "Helvetica"


def _ensure_ticket_token(visitor):
    if visitor.ticket_token:
        return visitor.ticket_token
    token = _build_ticket_token(visitor.id)
    visitor.ticket_token = token
    visitor.save(update_fields=["ticket_token"])
    return token


def _get_visitor_by_ticket_token(token):
    try:
        payload = signing.loads(token, salt="icee-ticket")
        visitor_id = payload.get("visitor_id")
    except (BadSignature, SignatureExpired, ValueError, TypeError):
        raise Http404(_("Билет недействителен или срок ссылки истек."))
    if not visitor_id:
        raise Http404(_("Билет не найден."))
    try:
        visitor = ExhibitionVisitor.objects.get(id=visitor_id)
        if visitor.ticket_token and visitor.ticket_token != token:
            raise Http404(_("Билет недействителен."))
        if not visitor.ticket_token:
            visitor.ticket_token = token
            visitor.save(update_fields=["ticket_token"])
        return visitor
    except ExhibitionVisitor.DoesNotExist:
        raise Http404(_("Билет не найден."))


def exhibition_ticket(request, token):
    visitor = _get_visitor_by_ticket_token(token)
    if REPORTLAB_AVAILABLE:
        return redirect("exhibition_ticket_pdf", token=visitor.ticket_token or token)
    ticket_url = request.build_absolute_uri(reverse("exhibition_ticket", args=[token]))
    return render(
        request,
        "registration/exhibition_ticket.html",
        {
            "visitor": visitor,
            "ticket_token": visitor.ticket_token or token,
            "ticket_qr_data_uri": _build_qr_data_uri(ticket_url),
        },
    )


def exhibition_ticket_pdf(request, token):
    if not REPORTLAB_AVAILABLE:
        return redirect("exhibition_ticket", token=token)

    visitor = _get_visitor_by_ticket_token(token)
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="icee-ticket-{visitor.id}.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    font_name = _get_pdf_font_name()

    p.setFillColorRGB(0.11, 0.31, 0.85)
    p.rect(0, height - 50 * mm, width, 50 * mm, fill=1, stroke=0)
    p.setFillColorRGB(1, 1, 1)
    p.setFont(font_name, 24)
    p.drawString(20 * mm, height - 28 * mm, "ICEE 2026")
    p.setFont(font_name, 12)
    p.drawString(20 * mm, height - 36 * mm, "ЭЛЕКТРОННЫЙ БИЛЕТ")

    p.setFillColorRGB(0.12, 0.16, 0.23)
    p.setFont(font_name, 16)
    p.drawString(20 * mm, height - 70 * mm, "Посетитель:")
    p.setFont(font_name, 20)
    full_name = f"{visitor.last_name} {visitor.first_name} {visitor.middle_name or ''}".strip()
    p.drawString(20 * mm, height - 82 * mm, full_name)

    ticket_url = request.build_absolute_uri(reverse("exhibition_ticket", args=[token]))
    qr_reader = _build_qr_image_reader(ticket_url)
    p.drawImage(qr_reader, width - 72 * mm, height - 136 * mm, 50 * mm, 50 * mm, mask="auto")

    p.setFont(font_name, 12)
    p.drawString(20 * mm, height - 100 * mm, f"Компания: {visitor.company}")
    p.drawString(20 * mm, height - 108 * mm, f"Email: {visitor.email}")
    local_created_at = timezone.localtime(visitor.created_at)
    p.drawString(20 * mm, height - 116 * mm, f"Дата регистрации: {local_created_at.strftime('%d.%m.%Y %H:%M')}")

    p.setFont(font_name, 13)
    p.drawString(20 * mm, height - 136 * mm, "Дата и время проведения:")
    p.setFont(font_name, 12)
    p.drawString(20 * mm, height - 145 * mm, "14-15 апреля: 10:00-18:00")
    p.drawString(20 * mm, height - 152 * mm, "16 апреля: 10:00-16:00")
    p.drawString(20 * mm, height - 163 * mm, "Адрес: г. Бишкек, ул. Ахунбаева, 97, Манеж КГАФКиС")

    p.setStrokeColorRGB(0.75, 0.8, 0.9)
    p.line(20 * mm, height - 176 * mm, width - 20 * mm, height - 176 * mm)
    p.setFont(font_name, 10)
    p.setFillColorRGB(0.3, 0.35, 0.42)
    p.drawString(20 * mm, height - 184 * mm, "Для входа предъявите билет в распечатанном или электронном виде.")
    p.drawString(20 * mm, height - 191 * mm, "Контакты: +996 775 000 005, info@icee.kg")

    p.showPage()
    p.save()
    return response


def _resolve_scan(raw_value):
    value = (raw_value or "").strip()
    if not value:
        raise Http404(_("Пустой код билета."))

    if "/ticket/" in value:
        match = re.search(r"/ticket/([^/]+)/?", value)
        if match:
            token = match.group(1)
            return _get_visitor_by_ticket_token(token), token

    if value.upper().startswith("ICEE-"):
        ticket_number = value.split("-", 1)[1]
        if ticket_number.isdigit():
            visitor = ExhibitionVisitor.objects.filter(id=int(ticket_number)).first()
            if visitor:
                return visitor, _ensure_ticket_token(visitor)

    if value.isdigit():
        visitor = ExhibitionVisitor.objects.filter(id=int(value)).first()
        if visitor:
            return visitor, _ensure_ticket_token(visitor)

    visitor = _get_visitor_by_ticket_token(value)
    return visitor, value


@staff_member_required
def exhibition_checkin(request):
    visitor = None
    token = None
    error = None
    scanned_value = ""
    if request.method == "POST":
        scanned_value = request.POST.get("ticket_code", "")
        try:
            visitor, token = _resolve_scan(scanned_value)
        except Http404 as exc:
            error = str(exc)
    return render(
        request,
        "registration/exhibition_checkin.html",
        {
            "visitor": visitor,
            "ticket_token": token,
            "scanned_value": scanned_value,
            "error": error,
        },
    )


@staff_member_required
def exhibition_ticket_print(request, token):
    visitor = _get_visitor_by_ticket_token(token)
    ticket_url = request.build_absolute_uri(reverse("exhibition_ticket", args=[token]))
    return render(
        request,
        "registration/exhibition_ticket_print.html",
        {
            "visitor": visitor,
            "ticket_code": _ticket_code(visitor.id),
            "ticket_qr_data_uri": _build_qr_data_uri(ticket_url),
        },
    )


def contacts_page(request):
    """Отдельная страница контактов."""
    return render(request, "contacts.html")
