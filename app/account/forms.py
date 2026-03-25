from django import forms
from django.utils.translation import gettext_lazy as _

from .models import ExhibitionVisitor


class EmailStepForm(forms.Form):
    """Шаг 1: ввод email перед регистрацией."""

    email = forms.EmailField(
        label=_("Введите адрес Вашей электронной почты:"),
        widget=forms.EmailInput(attrs={"placeholder": _("Ваш email"), "class": "form-input"}),
        required=True,
    )

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email and ExhibitionVisitor.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                _("На этот email уже зарегистрировались. Используйте другой адрес или свяжитесь с организаторами.")
            )
        return email


class ExhibitionRegistrationForm(forms.ModelForm):
    """Форма регистрации посетителя выставки."""

    visit_purposes = forms.MultipleChoiceField(
        label=_("Цель посещения выставки"),
        choices=ExhibitionVisitor.VISIT_PURPOSE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=True,
    )

    class Meta:
        model = ExhibitionVisitor
        fields = [
            "email",
            "last_name",
            "first_name",
            "middle_name",
            "phone_number",
            "city",
            "company",
            "exhibition_theme",
            "industry",
            "position",
            "visit_purposes",
            "source",
            "personal_data_consent",
        ]
        widgets = {
            "email": forms.EmailInput(attrs={"class": "form-input form-input-readonly", "readonly": "readonly"}),
            "last_name": forms.TextInput(attrs={"placeholder": "Иванов", "class": "form-input"}),
            "first_name": forms.TextInput(attrs={"placeholder": "Иван", "class": "form-input"}),
            "middle_name": forms.TextInput(attrs={"placeholder": "Иванович", "class": "form-input"}),
            "phone_number": forms.TextInput(
                attrs={"placeholder": "+996(___)___-___", "class": "form-input"}
            ),
            "city": forms.TextInput(
                attrs={"placeholder": "например, Бишкек", "class": "form-input"}
            ),
            "company": forms.TextInput(
                attrs={"placeholder": "ООО «Пример»", "class": "form-input"}
            ),
            "exhibition_theme": forms.Select(attrs={"class": "form-select"}),
            "industry": forms.Select(attrs={"class": "form-select"}),
            "position": forms.Select(attrs={"class": "form-select"}),
            "source": forms.Select(attrs={"class": "form-select"}),
            "personal_data_consent": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }
        labels = {
            "email": _("Email"),
            "last_name": _("Фамилия"),
            "first_name": _("Имя"),
            "middle_name": _("Отчество"),
            "phone_number": _("Мобильный телефон"),
            "city": _("Город"),
            "company": _("Компания"),
            "exhibition_theme": _("Выберите тематику выставки, которая Вас интересует больше"),
            "industry": _("Сфера деятельности Вашей организации"),
            "position": _("Кем Вы работаете в организации? Укажите должность"),
            "visit_purposes": _("Цель посещения выставки"),
            "source": _("Откуда Вы узнали о выставке?"),
            "personal_data_consent": _(
                "Заполнением данной формы посетитель подтверждает, что персональные данные, "
                "указанные в настоящей Форме, предоставлены им в соответствии с Законом КР "
                "от 14 апреля 2008 года №58 «Об информации персонального характера»"
            ),
        }

    def clean(self):
        cleaned = super().clean()
        visit_purposes = cleaned.get("visit_purposes")
        if not visit_purposes:
            self.add_error(
                "visit_purposes",
                forms.ValidationError(_("Выберите хотя бы одну цель посещения.")),
            )
        personal_data_consent = cleaned.get("personal_data_consent")
        if not personal_data_consent:
            self.add_error(
                "personal_data_consent",
                forms.ValidationError(_("Необходимо подтвердить согласие на обработку персональных данных.")),
            )
        return cleaned
