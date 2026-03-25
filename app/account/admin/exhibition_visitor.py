from django.contrib import admin
from django.contrib.postgres.fields import ArrayField
from django.core import signing
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from unfold.contrib.forms.widgets import ArrayWidget

from common.base_admin import BaseModelAdmin
from ..models import ExhibitionVisitor


@admin.register(ExhibitionVisitor)
class ExhibitionVisitorAdmin(BaseModelAdmin):
    list_display = ("last_name", "first_name", "email", "company", "city", "ticket_link", "created_at")
    list_filter = ("exhibition_theme", "industry", "source")
    search_fields = ("last_name", "first_name", "email", "company", "phone_number", "city")
    readonly_fields = ("created_at", "ticket_token", "ticket_link")
    ordering = ("-created_at",)
    list_per_page = 50

    formfield_overrides = {
        ArrayField: {
            "widget": ArrayWidget,
        },
    }

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj, change, **kwargs)
        form.base_fields["visit_purposes"].widget = ArrayWidget(
            choices=ExhibitionVisitor.VISIT_PURPOSE_CHOICES
        )
        return form

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not obj.ticket_token and obj.id:
            obj.ticket_token = signing.dumps({"visitor_id": obj.id}, salt="icee-ticket")
            obj.save(update_fields=["ticket_token"])

    @admin.display(description=_("Билет"))
    def ticket_link(self, obj):
        if not obj.ticket_url:
            return "—"
        return format_html('<a href="{}" target="_blank">Открыть</a>', obj.ticket_url)
