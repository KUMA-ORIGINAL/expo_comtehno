# Migration: JSONField -> ArrayField for visit_purposes

from django.contrib.postgres.fields import ArrayField
from django.db import migrations, models


def convert_json_to_array(apps, schema_editor):
    """Copy JSON list to new ArrayField (data format compatible)."""
    ExhibitionVisitor = apps.get_model("account", "ExhibitionVisitor")
    for obj in ExhibitionVisitor.objects.all():
        val = obj.visit_purposes
        obj.visit_purposes_new = [str(x) for x in val] if isinstance(val, list) else []
        obj.save()


class Migration(migrations.Migration):

    dependencies = [
        ("account", "0002_exhibition_visitor"),
    ]

    operations = [
        migrations.AddField(
            model_name="exhibitionvisitor",
            name="visit_purposes_new",
            field=ArrayField(
                models.CharField(blank=True, max_length=50),
                blank=True,
                default=list,
                size=None,
            ),
        ),
        migrations.RunPython(convert_json_to_array, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="exhibitionvisitor",
            name="visit_purposes",
        ),
        migrations.RenameField(
            model_name="exhibitionvisitor",
            old_name="visit_purposes_new",
            new_name="visit_purposes",
        ),
        migrations.AlterField(
            model_name="exhibitionvisitor",
            name="visit_purposes",
            field=ArrayField(
                base_field=models.CharField(blank=True, max_length=50),
                blank=True,
                default=list,
                help_text="Список выбранных целей",
                size=None,
                verbose_name="Цель посещения выставки",
            ),
        ),
    ]
