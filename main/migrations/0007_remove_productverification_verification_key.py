from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0006_productverification_verification_document"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="productverification",
            name="verification_key",
        ),
    ]
