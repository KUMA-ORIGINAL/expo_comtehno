from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField


class ExhibitionVisitor(models.Model):
    """Регистрация посетителя выставки."""

    EXHIBITION_THEME_CHOICES = [
        ("construction", _("Строительная индустрия")),
        ("energy", _("Энергетика и освещение")),
        ("security", _("Безопасность")),
        ("special_tech", _("Спецтехника")),
    ]

    INDUSTRY_CHOICES = [
        ("government", _("Государственный орган министерство/агентство/гос сектор")),
        ("construction", _("Строительная компания")),
        ("production", _("Производственная компания")),
        ("electric", _("Электроэнергетическая компания")),
        ("business_services", _("Услуги для бизнеса")),
        ("trade", _("Торговая компания (Дистрибьютор, и т.п.)")),
        ("education", _("Профессиональное учебное заведение")),
        ("transport", _("Транспортная компания")),
        ("nonprofit", _("Некоммерческая организация")),
        ("other", _("Другое")),
    ]

    POSITION_CHOICES = [
        ("owner", _("Собственник")),
        ("ceo", _("Генеральный директор")),
        ("director", _("Директор (коммерческий, технический, исполнительный)")),
        ("foreman", _("Прораб")),
        ("chief_engineer", _("Главный инженер")),
        ("chief_specialist", _("Главный специалист")),
        ("electrical_engineer", _("Инженер электрических сетей")),
        ("procurement", _("Специалист отдела закупок")),
        ("manager", _("Менеджер")),
        ("designer", _("Проектировщик")),
        ("architect", _("Архитектор")),
        ("designer_interior", _("Дизайнер")),
        ("other", _("Другое")),
    ]

    VISIT_PURPOSE_CHOICES = [
        ("purchase", _("Приобрести продукцию/услуги")),
        ("info", _("Получить информацию о продукции")),
        ("suppliers", _("Найти новых поставщиков")),
        ("contacts", _("Поддержать существующие деловые контакты")),
        ("seminar", _("Посетить семинар/конференцию/мастер-класс")),
        ("network", _("Пообщаться с коллегами")),
    ]

    SOURCE_CHOICES = [
        ("outdoor", _("Наружная реклама по городу")),
        ("internet", _("Реклама в Интернете")),
        ("social", _("Фэйсбук/Инстаграм")),
        ("tv", _("Телевидение")),
        ("radio", _("Радио")),
        ("call_center", _("Колл-центр")),
        ("invitation", _("Письмо с приглашением от организаторов")),
        ("flyer", _("Листовка")),
        ("friends", _("От друзей/коллег")),
        ("other", _("Другое")),
    ]

    email = models.EmailField(_("Email"), blank=False)
    last_name = models.CharField(_("Фамилия"), max_length=150)
    first_name = models.CharField(_("Имя"), max_length=150)
    middle_name = models.CharField(_("Отчество"), max_length=150, blank=True)
    phone_number = PhoneNumberField(_("Мобильный телефон"), region="KG")
    city = models.CharField(_("Город"), max_length=200)
    company = models.CharField(_("Компания"), max_length=300)
    exhibition_theme = models.CharField(
        _("Тематика выставки"),
        max_length=50,
        choices=EXHIBITION_THEME_CHOICES,
    )
    industry = models.CharField(
        _("Сфера деятельности организации"),
        max_length=50,
        choices=INDUSTRY_CHOICES,
    )
    position = models.CharField(
        _("Должность в организации"),
        max_length=50,
        choices=POSITION_CHOICES,
    )
    visit_purposes = ArrayField(
        models.CharField(max_length=50, blank=True),
        verbose_name=_("Цель посещения выставки"),
        default=list,
        blank=True,
        help_text=_("Список выбранных целей"),
    )
    source = models.CharField(
        _("Откуда узнали о выставке"),
        max_length=50,
        choices=SOURCE_CHOICES,
    )
    personal_data_consent = models.BooleanField(
        _("Согласие на обработку персональных данных"),
        default=False,
    )
    ticket_token = models.CharField(_("Токен билета"), max_length=255, blank=True, null=True, unique=True)
    created_at = models.DateTimeField(_("Дата регистрации"), auto_now_add=True)

    class Meta:
        verbose_name = _("Посетитель выставки")
        verbose_name_plural = _("Посетители выставки")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.last_name} {self.first_name} — {self.company}"

    @property
    def ticket_url(self):
        if not self.ticket_token:
            return ""
        return f"{settings.SITE_URL}{reverse('exhibition_ticket', args=[self.ticket_token])}"
    