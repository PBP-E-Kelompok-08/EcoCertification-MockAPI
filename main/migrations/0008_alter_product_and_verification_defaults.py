from django.db import migrations, models
import main.models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0007_remove_productverification_verification_key"),
    ]

    operations = [
        migrations.AlterField(
            model_name="product",
            name="eco_features",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AlterField(
            model_name="product",
            name="materials",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AlterField(
            model_name="product",
            name="origin",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AlterField(
            model_name="product",
            name="product_id",
            field=models.CharField(
                default=main.models.generate_next_product_id,
                max_length=50,
                primary_key=True,
                serialize=False,
            ),
        ),
        migrations.AlterField(
            model_name="product",
            name="slug",
            field=models.SlugField(blank=True, max_length=150, unique=True),
        ),
        migrations.AlterField(
            model_name="productverification",
            name="verification_id",
            field=models.CharField(
                default=main.models.generate_next_verification_id,
                max_length=50,
                primary_key=True,
                serialize=False,
            ),
        ),
    ]
