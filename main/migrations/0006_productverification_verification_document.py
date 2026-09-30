from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0005_remove_product_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="productverification",
            name="verification_document",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="verification_docs/",
            ),
        ),
    ]
