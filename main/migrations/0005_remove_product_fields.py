from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0004_productverification_verification_key"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="product",
            name="category",
        ),
        migrations.RemoveField(
            model_name="product",
            name="description",
        ),
        migrations.RemoveField(
            model_name="product",
            name="image_path",
        ),
        migrations.RemoveField(
            model_name="product",
            name="is_active",
        ),
    ]
