from django.urls import path

from main.views import *

app_name = "main"

urlpatterns = [
    path("api/products/", get_products, name="get_products"),
    path("api/products/<uuid:id>/", get_product_by_id, name="get_product_by_id"),
    path("api/products/<uuid:id>/certification",isCertified,name="isCertified")
]