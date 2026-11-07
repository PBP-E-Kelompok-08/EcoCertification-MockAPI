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
