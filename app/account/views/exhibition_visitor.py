from django.core.mail import EmailMultiAlternatives
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
import logging

from account.forms import ExhibitionRegistrationForm, EmailStepForm
from account.models.exhibition_visitor import ExhibitionVisitor
from account.ticket_utils import ensure_visitor_ticket_token, visitor_ticket_code

logger = logging.getLogger(__name__)


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
            ticket_token = ensure_visitor_ticket_token(visitor)
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
        "ticket_code": visitor_ticket_code(visitor.id),
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


def contacts_page(request):
    """Отдельная страница контактов."""
    return render(request, "contacts.html")
