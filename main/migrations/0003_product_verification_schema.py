import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0002_alter_certification_eco_rating"),
    ]

    operations = [
        migrations.CreateModel(
            name="Seller",
            fields=[
                (
                    "seller_id",
                    models.CharField(max_length=50, primary_key=True, serialize=False),
                ),
                ("name", models.CharField(max_length=255)),
                ("origin", models.CharField(max_length=255)),
            ],
            options={
                "ordering": ["seller_id"],
            },
        ),
        migrations.CreateModel(
            name="VerificationPartner",
            fields=[
                (
                    "partner_id",
                    models.CharField(max_length=50, primary_key=True, serialize=False),
                ),
                ("name", models.CharField(max_length=255)),
            ],
            options={
                "ordering": ["partner_id"],
            },
        ),
        migrations.CreateModel(
            name="Product",
            fields=[
                (
                    "product_id",
                    models.CharField(max_length=50, primary_key=True, serialize=False),
                ),
                ("name", models.CharField(max_length=120)),
                ("slug", models.SlugField(max_length=150, unique=True)),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("clothing", "Pakaian"),
                            ("daily_supplies", "Perlengkapan sehari-hari"),
                            ("home_kitchen", "Home & Kitchen"),
                            ("furniture", "Furniture"),
                            ("beauty_care", "Beauty & Care"),
                        ],
                        max_length=50,
                    ),
                ),
                ("description", models.TextField(blank=True, default="")),
                ("image_path", models.CharField(blank=True, default="", max_length=255)),
                ("materials", models.JSONField(default=list)),
                ("origin", models.CharField(max_length=255)),
                ("eco_features", models.JSONField(default=list)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "seller",
                    models.ForeignKey(
                        blank=True,
                        db_column="seller_id",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="products",
                        to="main.seller",
                    ),
                ),
            ],
            options={
                "ordering": ["product_id"],
            },
        ),
        migrations.CreateModel(
            name="ProductVerification",
            fields=[
                (
                    "verification_id",
                    models.CharField(max_length=50, primary_key=True, serialize=False),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Menunggu verifikasi"),
                            ("verified", "Terverifikasi"),
                            ("rejected", "Tidak memenuhi kriteria"),
                            ("expired", "Verifikasi kedaluwarsa"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("tested_at", models.DateField(blank=True, null=True)),
                ("valid_until", models.DateField(blank=True, null=True)),
                ("recycled_material_percent", models.IntegerField(blank=True, null=True)),
                ("reusable", models.BooleanField(blank=True, null=True)),
                ("eco_score", models.FloatField(blank=True, null=True)),
                ("summary", models.TextField(blank=True, null=True)),
                (
                    "partner",
                    models.ForeignKey(
                        blank=True,
                        db_column="partner_id",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="verifications",
                        to="main.verificationpartner",
                    ),
                ),
                (
                    "product",
                    models.OneToOneField(
                        db_column="product_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="verification",
                        to="main.product",
                    ),
                ),
            ],
            options={
                "ordering": ["verification_id"],
            },
        ),
        migrations.DeleteModel(
            name="Certification",
        ),
    ]

