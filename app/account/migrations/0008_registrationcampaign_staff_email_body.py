from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("account", "0007_registrationsubmission_ticket_token"),
    ]

    operations = [
        migrations.AlterField(
            model_name="registrationcampaign",
            name="applicant_email_body",
            field=models.TextField(
                blank=True,
                help_text="Подстановки: любой {ключ_поля} из формы; {applicant_name}, {applicant_email}; "
                "{campaign_title}, {campaign_subtitle}, {campaign_slug}, {submission_id}; "
                "{ticket_url}, {ticket_pdf_url}, {ticket_code}; {all_fields} — сводка всех полей заявки.",
                verbose_name="Текст письма заявителю (plain text)",
            ),
        ),
        migrations.AddField(
            model_name="registrationcampaign",
            name="staff_email_body",
            field=models.TextField(
                blank=True,
                help_text="Если заполнено — уходит этот текст (с подстановками). Если пусто — автоматическая сводка полей и ссылка на билет. "
                "Те же плейсхолдеры, что и у письма заявителю: {all_fields}, {ticket_pdf_url}, поля формы {ключ}, и т.д.",
                verbose_name="Текст письма организаторам (plain text)",
            ),
        ),
    ]
