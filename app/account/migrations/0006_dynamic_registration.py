# Generated manually

from django.db import migrations, models
import django.db.models.deletion


def seed_registration_forms(apps, schema_editor):
    RegistrationCampaign = apps.get_model("account", "RegistrationCampaign")
    RegistrationField = apps.get_model("account", "RegistrationField")

    c1 = RegistrationCampaign.objects.create(
        slug="ucastie-bishkek-2026",
        title="ЗАЯВКА НА УЧАСТИЕ",
        subtitle="г. Бишкек, 28-29 мая 2026 года",
        is_active=True,
        sort_order=10,
        allow_duplicate_submissions=False,
        applicant_email_field_key="contact_email",
        applicant_name_field_keys="last_name,first_name,middle_name",
        send_applicant_confirmation=True,
        applicant_email_subject="Заявка на участие получена",
        applicant_email_body=(
            "Здравствуйте, {first_name} {middle_name} {last_name}!\n\n"
            "Ваша заявка на участие принята. Мы свяжемся с вами по email: {contact_email}.\n\n"
            "С уважением,\nоргкомитет"
        ),
        notify_staff=True,
        staff_notification_emails="",
        staff_email_subject="Новая заявка на участие (Бишкек, 28–29 мая 2026)",
        success_message="",
    )
    fields1 = [
        ("last_name", "Фамилия", "text", "", True, 10),
        ("first_name", "Имя", "text", "", True, 20),
        ("middle_name", "Отчество", "text", "", True, 30),
        ("workplace", "Место работы (учёбы) (полное название)", "text", "", True, 40),
        ("position_degree", "Должность, учёная степень, звание", "text", "", True, 50),
        ("contact_email", "E-mail для переписки", "email", "", True, 60),
        ("phone", "Контактный телефон", "phone", "", True, 70),
        ("report_title", "Название доклада", "text", "", True, 80),
        ("coauthors", "Соавтор(ы)", "textarea", "", True, 90),
        (
            "participation_type",
            "Форма участия",
            "radio",
            "in_person|Очная\nremote|Дистанционная",
            True,
            100,
        ),
    ]
    for key, label, ftype, choices, required, so in fields1:
        RegistrationField.objects.create(
            campaign=c1,
            key=key,
            label=label,
            field_type=ftype,
            choices_text=choices,
            required=required,
            sort_order=so,
        )

    c2 = RegistrationCampaign.objects.create(
        slug="vtoraya-registraciya",
        title="Вторая регистрация",
        subtitle="Настройте заголовок, подзаголовок и поля в админке",
        is_active=True,
        sort_order=20,
        allow_duplicate_submissions=False,
        applicant_email_field_key="email",
        applicant_name_field_keys="full_name",
        send_applicant_confirmation=True,
        applicant_email_subject="Заявка получена",
        applicant_email_body="Спасибо, {full_name}! Ваша заявка принята.",
        notify_staff=True,
        staff_notification_emails="",
        staff_email_subject="Новая заявка (вторая форма)",
        success_message="",
    )
    fields2 = [
        ("full_name", "ФИО", "text", "", True, 10),
        ("email", "E-mail", "email", "", True, 20),
        ("comment", "Комментарий", "textarea", "", False, 30),
    ]
    for key, label, ftype, choices, required, so in fields2:
        RegistrationField.objects.create(
            campaign=c2,
            key=key,
            label=label,
            field_type=ftype,
            choices_text=choices,
            required=required,
            sort_order=so,
        )


def unseed_registration_forms(apps, schema_editor):
    RegistrationCampaign = apps.get_model("account", "RegistrationCampaign")
    RegistrationCampaign.objects.filter(slug__in=["ucastie-bishkek-2026", "vtoraya-registraciya"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("account", "0005_exhibitionvisitor_ticket_token"),
    ]

    operations = [
        migrations.CreateModel(
            name="RegistrationCampaign",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=80, unique=True, verbose_name="Код в URL")),
                ("title", models.CharField(max_length=255, verbose_name="Заголовок формы")),
                ("subtitle", models.CharField(blank=True, max_length=500, verbose_name="Подзаголовок (дата, место)")),
                ("is_active", models.BooleanField(default=True, verbose_name="Форма открыта")),
                ("sort_order", models.PositiveSmallIntegerField(default=0, verbose_name="Порядок в списке")),
                (
                    "allow_duplicate_submissions",
                    models.BooleanField(default=False, verbose_name="Разрешить повторные заявки с тем же email"),
                ),
                (
                    "applicant_email_field_key",
                    models.SlugField(
                        default="contact_email",
                        help_text="Для проверки дубликатов и отправки копии заявителю.",
                        max_length=64,
                        verbose_name="Ключ поля с email заявителя",
                    ),
                ),
                (
                    "applicant_name_field_keys",
                    models.CharField(
                        default="last_name,first_name,middle_name",
                        help_text="Например: last_name,first_name,middle_name",
                        max_length=200,
                        verbose_name="Ключи ФИО через запятую",
                    ),
                ),
                ("send_applicant_confirmation", models.BooleanField(default=True, verbose_name="Отправить письмо заявителю")),
                ("applicant_email_subject", models.CharField(blank=True, max_length=255, verbose_name="Тема письма заявителю")),
                (
                    "applicant_email_body",
                    models.TextField(
                        blank=True,
                        help_text="Подстановки: {ключ_поля} — значение из заявки.",
                        verbose_name="Текст письма заявителю",
                    ),
                ),
                ("notify_staff", models.BooleanField(default=True, verbose_name="Уведомить организаторов по email")),
                (
                    "staff_notification_emails",
                    models.TextField(blank=True, verbose_name="Email организаторов (по одному в строке)"),
                ),
                ("staff_email_subject", models.CharField(blank=True, max_length=255, verbose_name="Тема письма организаторам")),
                (
                    "success_message",
                    models.TextField(
                        blank=True,
                        help_text="Если пусто — показывается стандартное сообщение.",
                        verbose_name="Текст на странице «Спасибо»",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Регистрация / форма заявки",
                "verbose_name_plural": "Регистрации и формы",
                "ordering": ["sort_order", "id"],
            },
        ),
        migrations.CreateModel(
            name="RegistrationField",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.SlugField(max_length=64, verbose_name="Ключ поля (латиница, _)")),
                ("label", models.CharField(max_length=255, verbose_name="Подпись")),
                ("field_type", models.CharField(choices=[
                    ("text", "Одна строка"),
                    ("textarea", "Многострочный текст"),
                    ("email", "Email"),
                    ("phone", "Телефон"),
                    ("radio", "Один вариант из списка"),
                ], max_length=20, verbose_name="Тип")),
                (
                    "choices_text",
                    models.TextField(
                        blank=True,
                        help_text="Каждая строка: значение|Подпись, например: in_person|Очная",
                        verbose_name="Варианты (для списка)",
                    ),
                ),
                ("required", models.BooleanField(default=True, verbose_name="Обязательное")),
                ("sort_order", models.PositiveSmallIntegerField(default=0, verbose_name="Порядок")),
                (
                    "campaign",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="fields",
                        to="account.registrationcampaign",
                        verbose_name="Форма",
                    ),
                ),
            ],
            options={
                "verbose_name": "Поле формы",
                "verbose_name_plural": "Поля формы",
                "ordering": ["sort_order", "id"],
            },
        ),
        migrations.CreateModel(
            name="RegistrationSubmission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("data", models.JSONField(default=dict, verbose_name="Данные формы")),
                ("applicant_email", models.EmailField(blank=True, db_index=True, max_length=254, verbose_name="Email заявителя")),
                ("applicant_name", models.CharField(blank=True, max_length=500, verbose_name="ФИО / имя")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Подано")),
                (
                    "campaign",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="submissions",
                        to="account.registrationcampaign",
                        verbose_name="Форма",
                    ),
                ),
            ],
            options={
                "verbose_name": "Заявка",
                "verbose_name_plural": "Заявки",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="registrationfield",
            constraint=models.UniqueConstraint(fields=("campaign", "key"), name="uniq_registration_field_per_campaign"),
        ),
        migrations.RunPython(seed_registration_forms, unseed_registration_forms),
    ]
