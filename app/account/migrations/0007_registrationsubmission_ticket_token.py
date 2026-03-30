from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("account", "0006_dynamic_registration"),
    ]

    operations = [
        migrations.AddField(
            model_name="registrationsubmission",
            name="ticket_token",
            field=models.CharField(
                blank=True,
                max_length=255,
                null=True,
                unique=True,
                verbose_name="Токен электронного билета",
            ),
        ),
    ]
