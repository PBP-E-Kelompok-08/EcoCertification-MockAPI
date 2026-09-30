from django.urls import path

from main.views import (
    get_product_by_id,
    get_products,
    get_sellers,
    get_verification_partners,
    isCertified,
    upload_verification_document,
)

app_name = "main"

urlpatterns = [
    path("api/verify/document/", upload_verification_document, name="upload_verification_document"),
    path("api/products/", get_products, name="get_products"),
    path("api/products/<str:id>/", get_product_by_id, name="get_product_by_id"),
    path("api/products/<str:id>/certification/", isCertified, name="isCertified"),
    path("api/products/<str:id>/document/", upload_verification_document, name="upload_product_document"),
    path("api/sellers/", get_sellers, name="get_sellers"),
    path("api/verification-partners/", get_verification_partners, name="get_verification_partners"),
]