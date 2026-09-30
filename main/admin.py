from django.contrib import admin
from main.models import (
    Product,
    ProductVerification,
    Seller,
    VerificationPartner,
)


class ProductVerificationInline(admin.StackedInline):
    model = ProductVerification
    extra = 0
    can_delete = False
    readonly_fields = (
        "verification_id",
        "product",
        "verification_document",
    )
    fields = (
        "verification_id",
        "verification_document",
        "status",
        "partner",
        "tested_at",
        "valid_until",
        "recycled_material_percent",
        "reusable",
        "eco_score",
        "summary",
    )


@admin.register(Seller)
class SellerAdmin(admin.ModelAdmin):
    list_display = ("seller_id", "name", "origin")
    search_fields = ("seller_id", "name", "origin")


@admin.register(VerificationPartner)
class VerificationPartnerAdmin(admin.ModelAdmin):
    list_display = ("partner_id", "name")
    search_fields = ("partner_id", "name")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("product_id", "name", "seller", "origin")
    list_filter = ("seller", "origin")
    search_fields = ("product_id", "name", "slug", "origin")
    inlines = [ProductVerificationInline]


@admin.register(ProductVerification)
class ProductVerificationAdmin(admin.ModelAdmin):
    list_display = (
        "verification_id",
        "product",
        "status",
        "partner",
        "tested_at",
        "valid_until",
        "reusable",
        "verification_document",
    )
    list_filter = ("status", "reusable", "partner")
    search_fields = (
        "verification_id",
        "product__product_id",
        "product__name",
    )
    readonly_fields = (
        "verification_id",
        "product",
        "verification_document",
    )
    fields = (
        "verification_id",
        "product",
        "verification_document",
        "status",
        "partner",
        "tested_at",
        "valid_until",
        "recycled_material_percent",
        "reusable",
        "eco_score",
        "summary",
    )