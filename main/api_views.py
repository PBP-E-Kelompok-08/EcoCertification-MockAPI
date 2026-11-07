from django.db import OperationalError, ProgrammingError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Product, ProductVerification, Seller, VerificationPartner
from .serializers import (
    ProductSerializer,
    ProductVerificationSerializer,
    SellerSerializer,
    VerificationPartnerSerializer,
)
from .views import (
    load_raw_products,
    load_raw_sellers,
    load_raw_verification_partners,
    sync_data_from_files,
)


def _public_raw_product(product):
    """Return seed data without exposing a verification document field."""
    public_product = dict(product)
    verification = public_product.get("verification")
    if isinstance(verification, dict):
        public_product["verification"] = {
            key: value
            for key, value in verification.items()
            if key != "verification_document"
        }
    return public_product


def _product_queryset():
    if not Product.objects.exists():
        sync_data_from_files()
    return Product.objects.select_related(
        "seller",
        "verification",
        "verification__partner",
    ).all()


class ProductListAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            products = list(_product_queryset())
            eco_feature = request.query_params.get("eco_feature", "").strip()
            verification_status = (
                request.query_params.get("verification_status", "").strip()
                or request.query_params.get("status", "").strip()
            )
            seller_id = request.query_params.get("seller_id", "").strip()

            if eco_feature:
                products = [p for p in products if eco_feature in (p.eco_features or [])]
            if verification_status:
                products = [
                    p
                    for p in products
                    if hasattr(p, "verification")
                    and p.verification.status == verification_status
                ]
            if seller_id:
                products = [p for p in products if p.seller_id == seller_id]

            data = ProductSerializer(products, many=True).data
        except (OperationalError, ProgrammingError):
            products = [_public_raw_product(p) for p in load_raw_products()]
            eco_feature = request.query_params.get("eco_feature", "").strip()
            verification_status = (
                request.query_params.get("verification_status", "").strip()
                or request.query_params.get("status", "").strip()
            )
            seller_id = request.query_params.get("seller_id", "").strip()
            if eco_feature:
                products = [p for p in products if eco_feature in (p.get("eco_features") or [])]
            if verification_status:
                products = [
                    p
                    for p in products
                    if p.get("verification")
                    and p["verification"].get("status") == verification_status
                ]
            if seller_id:
                products = [p for p in products if p.get("seller_id") == seller_id]
            data = products

        return Response({"meta": {"count": len(data)}, "data": data})


class ProductDetailAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, product_id):
        try:
            product = _product_queryset().filter(pk=product_id).first()
            if product is not None:
                return Response({"meta": {}, "data": ProductSerializer(product).data})
        except (OperationalError, ProgrammingError):
            raw_product = next(
                (
                    _public_raw_product(p)
                    for p in load_raw_products()
                    if p.get("product_id") == product_id
                ),
                None,
            )
            if raw_product is not None:
                return Response({"meta": {}, "data": raw_product})

        return Response(
            {
                "meta": {},
                "error": {
                    "code": "PRODUCT_NOT_FOUND",
                    "message": "Produk tidak ditemukan",
                },
            },
            status=404,
        )


class ProductCertificationAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, product_id):
        try:
            product = _product_queryset().filter(pk=product_id).first()
            if product is not None:
                try:
                    verification = product.verification
                except ProductVerification.DoesNotExist:
                    verification = None
                certification = bool(verification and verification.certification)
                return Response(
                    {
                        "meta": {},
                        "data": {
                            "product_id": product.product_id,
                            "certification": certification,
                            "verification": (
                                ProductVerificationSerializer(verification).data
                                if verification
                                else None
                            ),
                        },
                        "certification": certification,
                    }
                )
        except (OperationalError, ProgrammingError):
            raw_product = next(
                (
                    _public_raw_product(p)
                    for p in load_raw_products()
                    if p.get("product_id") == product_id
                ),
                None,
            )
            if raw_product is not None:
                verification = raw_product.get("verification")
                certification = bool(
                    verification and verification.get("status") == "verified"
                )
                return Response(
                    {
                        "meta": {},
                        "data": {
                            "product_id": product_id,
                            "certification": certification,
                            "verification": verification,
                        },
                        "certification": certification,
                    }
                )

        return Response(
            {
                "meta": {},
                "error": {
                    "code": "PRODUCT_NOT_FOUND",
                    "message": "Produk tidak ditemukan",
                },
            },
            status=404,
        )


class SellerListAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            if not Seller.objects.exists():
                sync_data_from_files()
            data = SellerSerializer(Seller.objects.all(), many=True).data
        except (OperationalError, ProgrammingError):
            data = load_raw_sellers()
        return Response({"meta": {"count": len(data)}, "data": data})


class VerificationPartnerListAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            if not VerificationPartner.objects.exists():
                sync_data_from_files()
            data = VerificationPartnerSerializer(
                VerificationPartner.objects.all(),
                many=True,
            ).data
        except (OperationalError, ProgrammingError):
            data = load_raw_verification_partners()
        return Response({"meta": {"count": len(data)}, "data": data})
