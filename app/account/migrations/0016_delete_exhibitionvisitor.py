# Generated after removing the legacy ExhibitionVisitor flow.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("account", "0015_registrationemailsender_and_sender_address"),
    ]

    operations = [
        migrations.DeleteModel(
            name="ExhibitionVisitor",
        ),
    ]
