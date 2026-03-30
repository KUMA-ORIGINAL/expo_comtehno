import logging

from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

from account.models import RegistrationCampaign
from account.registration_forms import build_dynamic_registration_form_class
from common.tasks import queue_registration_submission_emails

logger = logging.getLogger(__name__)


def registration_index(request):
    campaigns = RegistrationCampaign.objects.filter(is_active=True).order_by("sort_order", "id")
    return render(request, "registration/campaign_list.html", {"campaigns": campaigns})


def registration_form(request, slug):
    campaign = get_object_or_404(RegistrationCampaign, slug=slug, is_active=True)
    if not campaign.fields.exists():
        return render(
            request,
            "registration/form_unavailable.html",
            {"campaign": campaign, "message": _("Форма пока не настроена. Загляните позже.")},
            status=503,
        )

    try:
        FormClass = build_dynamic_registration_form_class(campaign)
    except ValidationError as exc:
        logger.warning("Registration campaign '%s' is misconfigured: %s", campaign.slug, exc)
        return render(
            request,
            "registration/form_unavailable.html",
            {
                "campaign": campaign,
                "message": _("Форма временно недоступна. Организаторы обновляют её настройки."),
            },
            status=503,
        )
    language_code = (get_language() or "ru").split("-", 1)[0]

    if request.method == "POST":
        form = FormClass(request.POST, campaign=campaign, language_code=language_code)
        if form.is_valid():
            with transaction.atomic():
                submission = form.save_submission()
                transaction.on_commit(lambda sid=submission.id: queue_registration_submission_emails(sid))
            return redirect("registration_success", slug=campaign.slug)
    else:
        form = FormClass(campaign=campaign, language_code=language_code)

    return render(
        request,
        "registration/dynamic_register.html",
        {"campaign": campaign, "form": form},
    )


def registration_success(request, slug):
    campaign = get_object_or_404(RegistrationCampaign, slug=slug, is_active=True)
    return render(request, "registration/dynamic_success.html", {"campaign": campaign})
