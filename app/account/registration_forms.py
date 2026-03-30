from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from phonenumber_field.formfields import PhoneNumberField

from account.models import RegistrationField, RegistrationSubmission, parse_field_choices
from account.ticket_utils import ensure_submission_ticket_token


class BaseDynamicRegistrationForm(forms.Form):
    campaign = None
    language_code = "ru"
    radio_fields_with_other = ()

    def __init__(self, *args, campaign=None, language_code="ru", **kwargs):
        self.campaign = campaign
        self.language_code = (language_code or "ru").strip().lower()
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()

        # Convert "__other__" option into a custom text value and drop helper fields.
        for field_key in getattr(self, "radio_fields_with_other", ()):
            other_key = f"{field_key}__other"
            selected_value = (cleaned.get(field_key) or "").strip()
            other_value = (cleaned.get(other_key) or "").strip()

            if selected_value == "__other__":
                if not other_value:
                    self.add_error(other_key, _("Укажите свой вариант."))
                    cleaned.pop(field_key, None)
                else:
                    cleaned[field_key] = other_value

            cleaned.pop(other_key, None)

        if not self.campaign or self.campaign.allow_duplicate_submissions:
            return cleaned
        key = (self.campaign.applicant_email_field_key or "").strip()
        if not key or key not in self.fields:
            return cleaned
        email = (cleaned.get(key) or "").strip()
        if not email:
            return cleaned
        if RegistrationSubmission.objects.filter(
            campaign=self.campaign,
            applicant_email__iexact=email,
        ).exists():
            raise ValidationError(
                _("На этот адрес уже подана заявка по этой форме. При необходимости свяжитесь с организаторами.")
            )
        return cleaned

    def normalized_data(self) -> dict:
        out = {}
        for key, value in self.cleaned_data.items():
            if value is None:
                out[key] = ""
                continue
            out[key] = _serialize_for_json_storage(value)
        return out

    def save_submission(self) -> RegistrationSubmission:
        submission = RegistrationSubmission(
            campaign=self.campaign,
            data=self.normalized_data(),
            language_code=self.language_code or "ru",
        )
        submission.apply_applicant_snapshot()
        submission.save()
        ensure_submission_ticket_token(submission)
        return submission


def _serialize_for_json_storage(value):
    """Телефон из django-phonenumber-field: as_international может быть методом или свойством."""
    ai = getattr(value, "as_international", None)
    if ai is not None:
        return str(ai()) if callable(ai) else str(ai)
    if callable(getattr(value, "as_e164", None)):
        return str(value.as_e164())
    return value


def build_dynamic_registration_form_class(campaign):
    field_defs = list(
        RegistrationField.objects.filter(campaign=campaign).order_by("sort_order", "id")
    )
    campaign.validate_configuration(field_defs=field_defs)
    attrs_input = {"class": "form-input"}
    attrs_textarea = {"class": "form-input", "rows": 4}

    form_fields = {}
    radio_fields_with_other = []

    for fd in field_defs:
        if fd.field_type == RegistrationField.TYPE_TEXT:
            form_fields[fd.key] = forms.CharField(
                label=fd.label,
                required=fd.required,
                widget=forms.TextInput(attrs=attrs_input),
            )
        elif fd.field_type == RegistrationField.TYPE_TEXTAREA:
            form_fields[fd.key] = forms.CharField(
                label=fd.label,
                required=fd.required,
                widget=forms.Textarea(attrs=attrs_textarea),
            )
        elif fd.field_type == RegistrationField.TYPE_EMAIL:
            form_fields[fd.key] = forms.EmailField(
                label=fd.label,
                required=fd.required,
                widget=forms.EmailInput(attrs=attrs_input),
            )
        elif fd.field_type == RegistrationField.TYPE_PHONE:
            form_fields[fd.key] = PhoneNumberField(
                label=fd.label,
                required=fd.required,
                region="KG",
                widget=forms.TextInput(attrs={**attrs_input, "placeholder": "+996 …"}),
            )
        elif fd.field_type == RegistrationField.TYPE_RADIO:
            choices = parse_field_choices(fd.choices_text)
            choices = list(choices) + [("__other__", _("Другое"))]
            form_fields[fd.key] = forms.ChoiceField(
                label=fd.label,
                required=fd.required,
                choices=choices,
                widget=forms.Select(
                    attrs={
                        "class": "form-select js-other-select",
                        "data-other-field": f"{fd.key}__other",
                    }
                ),
            )
            form_fields[f"{fd.key}__other"] = forms.CharField(
                label=_("Другое (уточните)"),
                required=False,
                widget=forms.TextInput(
                    attrs={
                        "class": "form-input",
                        "placeholder": _("Укажите свой вариант"),
                    }
                ),
            )
            radio_fields_with_other.append(fd.key)
        else:
            form_fields[fd.key] = forms.CharField(label=fd.label, required=fd.required)

    return type(
        f"DynamicRegistrationForm_{campaign.pk}",
        (BaseDynamicRegistrationForm,),
        {**form_fields, "radio_fields_with_other": tuple(radio_fields_with_other)},
    )
