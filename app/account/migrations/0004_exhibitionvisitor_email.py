from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("account", "0003_alter_exhibitionvisitor_visit_purposes"),
    ]

    operations = [
        migrations.AddField(
            model_name="exhibitionvisitor",
            name="email",
            field=models.EmailField(default="visitor@example.com", max_length=254, verbose_name="Email"),
            preserve_default=False,
        ),
    ]
