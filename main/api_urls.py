from django.urls import path

from .api_views import (
    ProductCertificationAPIView,
    ProductDetailAPIView,
    ProductListAPIView,
    SellerListAPIView,
    VerificationDetailAPIView,
    VerificationDocumentUploadAPIView,
    VerificationPartnerListAPIView,
)


app_name = "main_api"

urlpatterns = [
    path("products/", ProductListAPIView.as_view(), name="products"),
    path("products/<str:product_id>/", ProductDetailAPIView.as_view(), name="product-detail"),
    path(
        "products/<str:product_id>/certification/",
        ProductCertificationAPIView.as_view(),
        name="product-certification",
    ),
    path(
        "products/<str:product_id>/document/",
        VerificationDocumentUploadAPIView.as_view(),
        name="product-document",
    ),
    path(
        "verify/document/",
        VerificationDocumentUploadAPIView.as_view(),
        name="verification-document",
    ),
    path(
        "verifications/<str:verification_id>/",
        VerificationDetailAPIView.as_view(),
        name="verification-detail",
    ),
    path("sellers/", SellerListAPIView.as_view(), name="sellers"),
    path(
        "verification-partners/",
        VerificationPartnerListAPIView.as_view(),
        name="verification-partners",
    ),
]
