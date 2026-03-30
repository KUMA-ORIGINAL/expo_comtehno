from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def copy_default_content_to_ru(apps, schema_editor):
    RegistrationCampaign = apps.get_model("account", "RegistrationCampaign")
    RegistrationField = apps.get_model("account", "RegistrationField")

    campaign_fields = [
        "title",
        "subtitle",
        "applicant_email_subject",
        "applicant_email_body",
        "staff_email_subject",
        "staff_email_body",
        "success_message",
        "participation_terms",
        "event_dates",
        "event_schedule",
        "event_location",
        "event_contact",
        "ticket_heading",
        "ticket_participant_label",
        "ticket_footer_note",
    ]
    for campaign in RegistrationCampaign.objects.all():
        changed = []
        for field_name in campaign_fields:
            ru_name = f"{field_name}_ru"
            if hasattr(campaign, ru_name):
                setattr(campaign, ru_name, getattr(campaign, field_name, ""))
                changed.append(ru_name)
        if changed:
            campaign.save(update_fields=changed)

    for field in RegistrationField.objects.all():
        changed = []
        if hasattr(field, "label_ru"):
            field.label_ru = field.label
            changed.append("label_ru")
        if hasattr(field, "choices_text_ru"):
            field.choices_text_ru = field.choices_text
            changed.append("choices_text_ru")
        if changed:
            field.save(update_fields=changed)


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0008_registrationcampaign_staff_email_body"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="registrationcampaign",
            name="event_contact",
            field=models.CharField(
                blank=True,
                help_text="Например: +996 775 000 005 · info@icee.kg",
                max_length=255,
                verbose_name="Контакты оргкомитета",
            ),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="event_dates",
            field=models.CharField(blank=True, max_length=255, verbose_name="Даты проведения"),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="event_location",
            field=models.CharField(blank=True, max_length=500, verbose_name="Место проведения"),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="event_schedule",
            field=models.CharField(blank=True, max_length=255, verbose_name="Время работы"),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="owner",
            field=models.ForeignKey(
                blank=True,
                help_text="Сотрудник, который управляет этой формой в админке.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="registration_campaigns",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Владелец формы",
            ),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="participation_terms",
            field=models.TextField(blank=True, help_text="Показываются под формой регистрации.", verbose_name="Условия участия"),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="ticket_footer_note",
            field=models.TextField(blank=True, help_text="Короткая памятка, которая выводится внизу страницы/билета.", verbose_name="Текст внизу билета"),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="ticket_heading",
            field=models.CharField(blank=True, default="", max_length=255, verbose_name="Заголовок подтверждения / билета"),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="ticket_participant_label",
            field=models.CharField(blank=True, default="", max_length=255, verbose_name="Подпись перед ФИО участника"),
        ),
        migrations.AddField(
            model_name="registrationsubmission",
            name="language_code",
            field=models.CharField(default="ru", max_length=10, verbose_name="Язык заявки"),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="title_ru",
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="title_en",
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="title_ky",
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="subtitle_ru",
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="subtitle_en",
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="subtitle_ky",
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="applicant_email_subject_ru",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="applicant_email_subject_en",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="applicant_email_subject_ky",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="applicant_email_body_ru",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="applicant_email_body_en",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="applicant_email_body_ky",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="staff_email_subject_ru",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="staff_email_subject_en",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="staff_email_subject_ky",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="staff_email_body_ru",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="staff_email_body_en",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="staff_email_body_ky",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="success_message_ru",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="success_message_en",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="success_message_ky",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="participation_terms_ru",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="participation_terms_en",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="participation_terms_ky",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="event_dates_ru",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="event_dates_en",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="event_dates_ky",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="event_schedule_ru",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="event_schedule_en",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="event_schedule_ky",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="event_location_ru",
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="event_location_en",
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="event_location_ky",
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="event_contact_ru",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="event_contact_en",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="event_contact_ky",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="ticket_heading_ru",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="ticket_heading_en",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="ticket_heading_ky",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="ticket_participant_label_ru",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="ticket_participant_label_en",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="ticket_participant_label_ky",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="ticket_footer_note_ru",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="ticket_footer_note_en",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="ticket_footer_note_ky",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="registrationfield",
            name="label_ru",
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="registrationfield",
            name="label_en",
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="registrationfield",
            name="label_ky",
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="registrationfield",
            name="choices_text_ru",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="registrationfield",
            name="choices_text_en",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="registrationfield",
            name="choices_text_ky",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.RunPython(copy_default_content_to_ru, migrations.RunPython.noop),
    ]
