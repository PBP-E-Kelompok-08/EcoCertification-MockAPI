import secrets
import string
from django.db import migrations, models


def _generate_verification_key():
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(32))


def populate_verification_keys(apps, schema_editor):
    ProductVerification = apps.get_model("main", "ProductVerification")
    for verification in ProductVerification.objects.all():
        if not verification.verification_key:
            verification.verification_key = _generate_verification_key()
            verification.save(update_fields=["verification_key"])


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0003_product_verification_schema"),
    ]

    operations = [
        migrations.AddField(
            model_name="productverification",
            name="verification_key",
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
        migrations.RunPython(
            populate_verification_keys,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="productverification",
            name="verification_key",
            field=models.CharField(
                default=_generate_verification_key,
                max_length=128,
                unique=True,
            ),
        ),
    ]

