from import_export import fields, resources
from django.utils.translation import gettext_lazy as _

from account.models import RegistrationField, RegistrationSubmission


class RegistrationSubmissionResource(resources.ModelResource):
    id = fields.Field(attribute="id", column_name=_("ID"))
    campaign = fields.Field(attribute="campaign__title", column_name=_("Форма"))
    applicant_name = fields.Field(attribute="applicant_name", column_name=_("ФИО / имя"))
    applicant_email = fields.Field(attribute="applicant_email", column_name=_("Email заявителя"))
    language_code = fields.Field(attribute="language_code", column_name=_("Язык заявки"))
    created_at = fields.Field(attribute="created_at", column_name=_("Подано"))

    _STATIC_FIELD_NAMES = (
        "id",
        "campaign",
        "applicant_name",
        "applicant_email",
        "language_code",
        "created_at",
    )

    class Meta:
        model = RegistrationSubmission
        fields = (
            "id",
            "campaign",
            "applicant_name",
            "applicant_email",
            "language_code",
            "created_at",
        )
        export_order = fields

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._dynamic_keys: list[str] = []

    @staticmethod
    def _format_value(value):
        if value is None:
            return ""
        if isinstance(value, bool):
            return "1" if value else "0"
        if isinstance(value, (list, tuple)):
            return ", ".join("" if v is None else str(v) for v in value)
        if isinstance(value, dict):
            return ", ".join(f"{k}: {v}" for k, v in value.items())
        return str(value)

    def _prepare_dynamic_fields(self, queryset):
        seen: list[str] = []
        seen_set: set[str] = set()
        campaign_ids: set[int] = set()
        for campaign_id, data in queryset.values_list("campaign_id", "data"):
            if campaign_id is not None:
                campaign_ids.add(campaign_id)
            if not isinstance(data, dict):
                continue
            for key in data.keys():
                if key not in seen_set:
                    seen_set.add(key)
                    seen.append(key)

        labels: dict[str, str] = {}
        if campaign_ids:
            field_qs = RegistrationField.objects.filter(
                campaign_id__in=campaign_ids
            ).values_list("key", "label", "sort_order")
            field_qs = sorted(field_qs, key=lambda row: (row[2], row[0]))
            ordered_known: list[str] = []
            for key, label, _sort in field_qs:
                labels.setdefault(key, label or key)
                if key in seen_set and key not in ordered_known:
                    ordered_known.append(key)
            extras = [k for k in seen if k not in ordered_known]
            seen = ordered_known + extras

        for static_name in self._STATIC_FIELD_NAMES:
            self.fields.pop(f"data_{static_name}", None)
        for existing in list(self.fields.keys()):
            if existing.startswith("data__"):
                self.fields.pop(existing, None)

        self._dynamic_keys = seen
        for key in seen:
            field_name = f"data__{key}"
            label = labels.get(key, key)
            self.fields[field_name] = fields.Field(column_name=label)

            def make_dehydrate(data_key):
                def _dehydrate(obj):
                    return self._format_value((obj.data or {}).get(data_key))

                return _dehydrate

            setattr(self, f"dehydrate_{field_name}", make_dehydrate(key))

    def before_export(self, queryset, *args, **kwargs):
        super().before_export(queryset, *args, **kwargs)
        self._prepare_dynamic_fields(queryset)

    def get_export_fields(self, fields=None):
        export_fields = list(super().get_export_fields(fields))
        for key in self._dynamic_keys:
            field = self.fields.get(f"data__{key}")
            if field is not None and field not in export_fields:
                export_fields.append(field)
        return export_fields

    def get_export_order(self):
        return list(self._STATIC_FIELD_NAMES) + [f"data__{key}" for key in self._dynamic_keys]
