from django.db import transaction
from rest_framework import serializers

from .models import (
    Product,
    ProductVerification,
    Seller,
    VerificationPartner,
    VerificationStatus,
)


class SellerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Seller
        fields = ["seller_id", "name", "origin"]
        read_only_fields = fields


class VerificationPartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerificationPartner
        fields = ["partner_id", "name"]
        read_only_fields = fields


class ProductVerificationSerializer(serializers.ModelSerializer):
    partner = VerificationPartnerSerializer(read_only=True)
    certification = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProductVerification
        fields = [
            "verification_id",
            "status",
            "partner",
            "tested_at",
            "valid_until",
            "recycled_material_percent",
            "reusable",
            "eco_score",
            "summary",
            "certification",
        ]
        read_only_fields = fields


class ProductSerializer(serializers.ModelSerializer):
    seller_id = serializers.CharField(read_only=True)
    verification = ProductVerificationSerializer(read_only=True)

    class Meta:
        model = Product
        fields = [
            "product_id",
            "name",
            "slug",
            "seller_id",
            "materials",
            "origin",
            "eco_features",
            "verification",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ProductSubmissionSerializer(serializers.Serializer):
    product_id = serializers.CharField(max_length=50, required=False)
    name = serializers.CharField(max_length=120)
    slug = serializers.SlugField(max_length=150, required=False)
    seller_id = serializers.CharField(max_length=50, required=False, allow_blank=True)
    seller_name = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
    )
    materials = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
    )
    origin = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        default="",
    )
    eco_features = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
    )
    verification_document = serializers.FileField(required=False, write_only=True)

    def validate_product_id(self, value):
        value = value.strip()
        if Product.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Product ID sudah digunakan.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        uploaded_file = validated_data.pop("verification_document", None)
        seller_id = validated_data.pop("seller_id", "").strip()
        seller_name = validated_data.pop("seller_name", "").strip()
        origin = validated_data.get("origin", "")

        seller = None
        if seller_id:
            seller, _ = Seller.objects.get_or_create(
                seller_id=seller_id,
                defaults={
                    "name": seller_name or seller_id,
                    "origin": origin,
                },
            )

        if not origin and seller is not None:
            validated_data["origin"] = seller.origin

        product = Product.objects.create(seller=seller, **validated_data)
        ProductVerification.objects.create(
            product=product,
            status=VerificationStatus.PENDING,
            verification_document=uploaded_file,
        )
        return product


class ProductUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    slug = serializers.SlugField(max_length=150, required=False)
    seller_id = serializers.CharField(max_length=50, required=False, allow_blank=True)
    seller_name = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
    )
    materials = serializers.ListField(
        child=serializers.CharField(),
        required=False,
    )
    origin = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
    )
    eco_features = serializers.ListField(
        child=serializers.CharField(),
        required=False,
    )
    verification_document = serializers.FileField(required=False, write_only=True)

    def validate_slug(self, value):
        products = Product.objects.filter(slug=value)
        if self.instance is not None:
            products = products.exclude(pk=self.instance.pk)
        if products.exists():
            raise serializers.ValidationError("Slug sudah digunakan.")
        return value

    @transaction.atomic
    def update(self, instance, validated_data):
        uploaded_file = validated_data.pop("verification_document", None)
        seller_was_provided = "seller_id" in validated_data
        seller_id = validated_data.pop("seller_id", "").strip()
        seller_name = validated_data.pop("seller_name", "").strip()

        if seller_was_provided:
            if seller_id:
                seller, _ = Seller.objects.get_or_create(
                    seller_id=seller_id,
                    defaults={
                        "name": seller_name or seller_id,
                        "origin": validated_data.get("origin", instance.origin),
                    },
                )
                instance.seller = seller
            else:
                instance.seller = None

        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        if uploaded_file is not None:
            verification, _ = ProductVerification.objects.get_or_create(
                product=instance,
                defaults={"status": VerificationStatus.PENDING},
            )
            verification.verification_document = uploaded_file
            verification.save(update_fields=["verification_document"])

        return instance


class VerificationDocumentUploadSerializer(serializers.Serializer):
    product_id = serializers.CharField(max_length=50, required=False)
    verification_id = serializers.CharField(max_length=50, required=False)
    verification_document = serializers.FileField(required=False, write_only=True)
    document = serializers.FileField(required=False, write_only=True)
    file = serializers.FileField(required=False, write_only=True)

    def validate(self, attrs):
        uploaded_file = (
            attrs.pop("verification_document", None)
            or attrs.pop("document", None)
            or attrs.pop("file", None)
        )
        if uploaded_file is None:
            raise serializers.ValidationError(
                {
                    "verification_document": (
                        "File wajib diunggah melalui multipart/form-data."
                    )
                }
            )
        attrs["uploaded_file"] = uploaded_file
        return attrs


class VerificationUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=VerificationStatus.choices)
    partner_id = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    tested_at = serializers.DateField(required=False, allow_null=True)
    valid_until = serializers.DateField(required=False, allow_null=True)
    recycled_material_percent = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=0,
        max_value=100,
    )
    reusable = serializers.BooleanField(required=False, allow_null=True)
    eco_score = serializers.FloatField(
        required=False,
        allow_null=True,
        min_value=0,
        max_value=100,
    )
    summary = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    def validate_partner_id(self, value):
        if value and not VerificationPartner.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Partner verifikasi tidak ditemukan.")
        return value

    def validate(self, attrs):
        tested_at = attrs.get("tested_at", self.instance.tested_at)
        valid_until = attrs.get("valid_until", self.instance.valid_until)
        if tested_at and valid_until and valid_until < tested_at:
            raise serializers.ValidationError(
                {"valid_until": "Tanggal berlaku tidak boleh sebelum tanggal pengujian."}
            )
        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        if "partner_id" in validated_data:
            partner_id = validated_data.pop("partner_id")
            instance.partner = (
                VerificationPartner.objects.get(pk=partner_id)
                if partner_id
                else None
            )

        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance
