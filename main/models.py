import re
from django.db import models
from django.utils.text import slugify


def generate_next_product_id() -> str:
    existing_ids = Product.objects.values_list("product_id", flat=True)
    max_num = 0
    for pid in existing_ids:
        match = re.match(r"^prd-(\d+)$", str(pid))
        if match:
            max_num = max(max_num, int(match.group(1)))
    return f"prd-{max_num + 1:03d}"


def generate_next_verification_id() -> str:
    existing_ids = ProductVerification.objects.values_list("verification_id", flat=True)
    max_num = 0
    for vid in existing_ids:
        match = re.match(r"^ver-(\d+)$", str(vid))
        if match:
            max_num = max(max_num, int(match.group(1)))
    return f"ver-{max_num + 1:03d}"


class VerificationStatus(models.TextChoices):
    PENDING = "pending", "Menunggu verifikasi"
    VERIFIED = "verified", "Terverifikasi"
    REJECTED = "rejected", "Tidak memenuhi kriteria"
    EXPIRED = "expired", "Verifikasi kedaluwarsa"


class Seller(models.Model):
    seller_id = models.CharField(max_length=50, primary_key=True)
    name = models.CharField(max_length=255)
    origin = models.CharField(max_length=255)

    class Meta:
        ordering = ["seller_id"]

    def __str__(self):
        return f"{self.seller_id} - {self.name}"

    def to_dict(self):
        return {
            "seller_id": self.seller_id,
            "name": self.name,
            "origin": self.origin,
        }


class VerificationPartner(models.Model):
    partner_id = models.CharField(max_length=50, primary_key=True)
    name = models.CharField(max_length=255)

    class Meta:
        ordering = ["partner_id"]

    def __str__(self):
        return f"{self.partner_id} - {self.name}"

    def to_dict(self):
        return {
            "partner_id": self.partner_id,
            "name": self.name,
        }


class Product(models.Model):
    product_id = models.CharField(
        max_length=50,
        primary_key=True,
        default=generate_next_product_id,
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=150, unique=True, blank=True)
    seller = models.ForeignKey(
        Seller,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
        db_column="seller_id",
    )
    materials = models.JSONField(default=list, blank=True)
    origin = models.CharField(max_length=255, blank=True, default="")
    eco_features = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["product_id"]

    def __str__(self):
        return f"{self.product_id} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.product_id:
            self.product_id = generate_next_product_id()
        if not self.slug:
            base_slug = slugify(self.name) or self.product_id
            slug_candidate = base_slug
            counter = 2
            while (
                Product.objects.filter(slug=slug_candidate)
                .exclude(pk=self.product_id)
                .exists()
            ):
                slug_candidate = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug_candidate
        super().save(*args, **kwargs)

    def to_dict(self):
        try:
            verification_data = self.verification.to_dict()
        except ProductVerification.DoesNotExist:
            verification_data = None

        return {
            "product_id": self.product_id,
            "name": self.name,
            "slug": self.slug,
            "seller_id": self.seller_id,
            "materials": self.materials,
            "origin": self.origin,
            "eco_features": self.eco_features,
            "verification": verification_data,
        }


class ProductVerification(models.Model):
    verification_id = models.CharField(
        max_length=50,
        primary_key=True,
        default=generate_next_verification_id,
    )
    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name="verification",
        db_column="product_id",
    )
    status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )
    partner = models.ForeignKey(
        VerificationPartner,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verifications",
        db_column="partner_id",
    )
    tested_at = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    recycled_material_percent = models.IntegerField(null=True, blank=True)
    reusable = models.BooleanField(null=True, blank=True)
    eco_score = models.FloatField(null=True, blank=True)
    summary = models.TextField(null=True, blank=True)
    verification_document = models.FileField(
        upload_to="verification_docs/",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["verification_id"]

    def __str__(self):
        return f"{self.verification_id} ({self.product_id} - {self.status})"

    def save(self, *args, **kwargs):
        if not self.verification_id:
            self.verification_id = generate_next_verification_id()
        super().save(*args, **kwargs)

    @property
    def certification(self):
        return self.status == VerificationStatus.VERIFIED

    def to_dict(self):
        return {
            "verification_id": self.verification_id,
            "status": self.status,
            "partner": self.partner.to_dict() if self.partner else None,
            "tested_at": (
                self.tested_at.isoformat()
                if hasattr(self.tested_at, "isoformat")
                else self.tested_at
            ),
            "valid_until": (
                self.valid_until.isoformat()
                if hasattr(self.valid_until, "isoformat")
                else self.valid_until
            ),
            "recycled_material_percent": self.recycled_material_percent,
            "reusable": self.reusable,
            "eco_score": self.eco_score,
            "summary": self.summary,
        }

