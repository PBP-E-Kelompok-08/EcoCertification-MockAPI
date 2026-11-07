from rest_framework import serializers

from .models import Product, ProductVerification, Seller, VerificationPartner


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
