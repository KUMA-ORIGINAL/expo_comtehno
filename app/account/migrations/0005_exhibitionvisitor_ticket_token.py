from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0004_exhibitionvisitor_email"),
    ]

    operations = [
        migrations.AddField(
            model_name="exhibitionvisitor",
            name="ticket_token",
            field=models.CharField(blank=True, null=True, max_length=255, unique=True, verbose_name="Токен билета"),
        ),
    ]

