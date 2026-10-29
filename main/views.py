import json
import secrets
from pathlib import Path

from django.conf import settings
from django.db import OperationalError, ProgrammingError, transaction
from django.http import JsonResponse
from django.utils.dateparse import parse_date
from django.views.decorators.csrf import csrf_exempt

from main.models import *

DATA_DIR = Path(settings.BASE_DIR) / "data"


def _authorized_writer(request):
    expected = settings.MOCK_API_WRITE_TOKEN
    supplied = request.headers.get("X-Mock-Api-Key", "")
    return bool(expected and supplied and secrets.compare_digest(supplied, expected))


def _unauthorized_writer_response():
    return JsonResponse({"success": False, "error": {"code": "UNAUTHORIZED", "message": "Kunci API tidak valid"}}, status=401)


def _read_json_file(file_path: Path):
    if not file_path.exists():
        return []
    with file_path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def load_raw_sellers():
    return _read_json_file(DATA_DIR / "reference" / "sellers.json")


def load_raw_verification_partners():
    return _read_json_file(DATA_DIR / "reference" / "verification-partners.json")


def load_raw_products():
    products_dir = DATA_DIR / "products"
    if not products_dir.exists():
        return []

    products_by_id = {}
    for json_file in sorted(products_dir.glob("*.json")):
        items = _read_json_file(json_file)
        if isinstance(items, list):
            for item in items:
                product_id = item.get("product_id")
                if product_id:
                    products_by_id[product_id] = item
    return list(products_by_id.values())


def sync_data_from_files():
    """Add missing seed products and verifications without replacing live records."""
    sellers_data = load_raw_sellers()
    partners_data = load_raw_verification_partners()
    products_data = load_raw_products()

    with transaction.atomic():
        for seller_item in sellers_data:
            Seller.objects.get_or_create(
                seller_id=seller_item["seller_id"],
                defaults={
                    "name": seller_item.get("name", ""),
                    "origin": seller_item.get("origin", ""),
                },
            )

        for partner_item in partners_data:
            VerificationPartner.objects.get_or_create(
                partner_id=partner_item["partner_id"],
                defaults={
                    "name": partner_item.get("name", ""),
                },
            )

        for product_item in products_data:
            seller_id = product_item.get("seller_id")
            seller_obj = None
            if seller_id:
                seller_obj = Seller.objects.filter(pk=seller_id).first()

            product_obj, _ = Product.objects.get_or_create(
                product_id=product_item["product_id"],
                defaults={
                    "name": product_item.get("name", ""),
                    "slug": product_item.get("slug", ""),
                    "seller": seller_obj,
                    "materials": product_item.get("materials") or [],
                    "origin": product_item.get("origin", ""),
                    "eco_features": product_item.get("eco_features") or [],
                },
            )

            verification_data = product_item.get("verification")
            if verification_data and verification_data.get("verification_id"):
                partner_data = verification_data.get("partner")
                partner_obj = None
                if isinstance(partner_data, dict) and partner_data.get("partner_id"):
                    partner_obj, _ = VerificationPartner.objects.get_or_create(
                        partner_id=partner_data["partner_id"],
                        defaults={"name": partner_data.get("name", "")},
                    )

                tested_at_raw = verification_data.get("tested_at")
                valid_until_raw = verification_data.get("valid_until")

                defaults = {
                    "product": product_obj,
                    "status": verification_data.get("status", "pending"),
                    "partner": partner_obj,
                    "tested_at": (
                        parse_date(tested_at_raw) if tested_at_raw else None
                    ),
                    "valid_until": (
                        parse_date(valid_until_raw) if valid_until_raw else None
                    ),
                    "recycled_material_percent": verification_data.get(
                        "recycled_material_percent"
                    ),
                    "reusable": verification_data.get("reusable"),
                    "eco_score": verification_data.get("eco_score"),
                    "summary": verification_data.get("summary"),
                }

                # Seed data must never overwrite an admin decision or a live submission.
                defaults.pop("product")
                ProductVerification.objects.get_or_create(
                    product=product_obj,
                    defaults=defaults,
                )


def _get_all_product_dicts():
    """Return all products as canonical dicts from DB (auto-seeding if empty), with JSON fallback."""
    try:
        if not Product.objects.exists():
            sync_data_from_files()
        queryset = Product.objects.select_related(
            "seller", "verification", "verification__partner"
        ).all()
        return [product.to_dict() for product in queryset]
    except (OperationalError, ProgrammingError):
        return load_raw_products()


def _product_not_found_response():
    return JsonResponse(
        {
            "meta": {},
            "error": {
                "code": "PRODUCT_NOT_FOUND",
                "message": "Produk tidak ditemukan",
            },
        },
        status=404,
    )


def _parse_list_field(raw_val):
    if isinstance(raw_val, list):
        return [str(x).strip() for x in raw_val if str(x).strip()]
    if isinstance(raw_val, str):
        raw_val = raw_val.strip()
        if not raw_val:
            return []
        try:
            parsed = json.loads(raw_val)
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if str(x).strip()]
        except ValueError:
            pass
        return [part.strip() for part in raw_val.split(",") if part.strip()]
    return []


def _extract_product_payload(request):
    """
    Extract product details from JSON body, nested JSON form field ('data'/'product'/'json'),
    or standard multipart/form-data fields.
    """
    data = {}
    content_type = (getattr(request, "content_type", "") or "").lower()

    if (
        "multipart/form-data" not in content_type
        and "application/x-www-form-urlencoded" not in content_type
    ):
        try:
            if request.body:
                parsed = json.loads(request.body.decode("utf-8"))
                if isinstance(parsed, dict):
                    data.update(parsed)
        except Exception:
            pass

    for json_field in ("data", "product", "json"):
        raw_json = request.POST.get(json_field)
        if raw_json:
            try:
                parsed = json.loads(raw_json)
                if isinstance(parsed, dict):
                    data.update(parsed)
            except ValueError:
                pass

    for key, value in request.POST.items():
        if key in ("data", "product", "json"):
            continue
        if key in ("materials", "eco_features"):
            values_list = request.POST.getlist(key)
            if len(values_list) > 1:
                data[key] = values_list
            else:
                data.setdefault(key, value)
        else:
            data.setdefault(key, value)

    return data


def _create_or_update_product_submission(payload, uploaded_file=None, explicit_product_id=None):
    """
    Fill Product model with the product details from POST (not the document)
    and ensure a ProductVerification record exists (storing verification_document if provided).
    """
    if not Product.objects.exists():
        sync_data_from_files()

    product_id = str(explicit_product_id or payload.get("product_id") or "").strip()
    name = str(payload.get("name") or "").strip()
    slug = str(payload.get("slug") or "").strip()
    origin = str(payload.get("origin") or "").strip()

    seller_info = payload.get("seller")
    seller_id = str(payload.get("seller_id") or "").strip()
    seller_name = str(payload.get("seller_name") or "").strip()
    seller_origin = origin

    if isinstance(seller_info, dict):
        seller_id = str(seller_info.get("seller_id") or seller_id).strip()
        seller_name = str(seller_info.get("name") or seller_name).strip()
        seller_origin = str(seller_info.get("origin") or seller_origin).strip()

    seller_obj = None
    if seller_id:
        seller_obj = Seller.objects.filter(pk=seller_id).first()
        if seller_obj is None:
            seller_obj = Seller.objects.create(
                seller_id=seller_id,
                name=seller_name or seller_id,
                origin=seller_origin or "",
            )

    if not origin and seller_obj:
        origin = seller_obj.origin

    materials = _parse_list_field(payload.get("materials"))
    eco_features = _parse_list_field(payload.get("eco_features"))

    existing_product = (
        Product.objects.filter(pk=product_id).first() if product_id else None
    )

    if existing_product is None and not name:
        return None, None, (
            "MISSING_PRODUCT_NAME",
            "Field 'name' wajib diisi untuk membuat produk baru",
            400,
        )

    with transaction.atomic():
        if existing_product:
            if name:
                existing_product.name = name
            if slug:
                existing_product.slug = slug
            if seller_obj is not None:
                existing_product.seller = seller_obj
            if "materials" in payload:
                existing_product.materials = materials
            if origin:
                existing_product.origin = origin
            if "eco_features" in payload:
                existing_product.eco_features = eco_features
            existing_product.save()
            product_obj = existing_product
        else:
            product_kwargs = {
                "name": name,
                "seller": seller_obj,
                "materials": materials,
                "origin": origin,
                "eco_features": eco_features,
            }
            if product_id:
                product_kwargs["product_id"] = product_id
            if slug:
                product_kwargs["slug"] = slug
            product_obj = Product(**product_kwargs)
            product_obj.save()

        verification_obj = ProductVerification.objects.filter(
            product=product_obj
        ).first()
        if verification_obj is None:
            verification_id = str(payload.get("verification_id") or "").strip()
            ver_kwargs = {
                "product": product_obj,
                "status": VerificationStatus.PENDING,
            }
            if verification_id:
                ver_kwargs["verification_id"] = verification_id
            verification_obj = ProductVerification(**ver_kwargs)

        if uploaded_file is not None:
            verification_obj.verification_document = uploaded_file

        verification_obj.save()

    return product_obj, verification_obj, None


@csrf_exempt
def get_products(request):
    if request.method == "POST":
        if not _authorized_writer(request):
            return _unauthorized_writer_response()
        payload = _extract_product_payload(request)
        uploaded_file = (
            request.FILES.get("verification_document")
            or request.FILES.get("document")
            or request.FILES.get("file")
        )
        product_obj, _, error_info = _create_or_update_product_submission(
            payload, uploaded_file=uploaded_file
        )
        if error_info:
            code, message, status_code = error_info
            return JsonResponse(
                {
                    "success": False,
                    "meta": {},
                    "error": {
                        "code": code,
                        "message": message,
                    },
                },
                status=status_code,
            )

        return JsonResponse(
            {
                "success": True,
                "message": "Produk berhasil disimpan dan menunggu verifikasi admin.",
                "meta": {},
                "data": product_obj.to_dict(),
            },
            status=201,
        )

    products = _get_all_product_dicts()

    eco_feature = request.GET.get("eco_feature", "").strip()
    verification_status = (
        request.GET.get("verification_status", "").strip()
        or request.GET.get("status", "").strip()
    )
    seller_id = request.GET.get("seller_id", "").strip()

    if eco_feature:
        products = [
            p for p in products if eco_feature in (p.get("eco_features") or [])
        ]

    if verification_status:
        products = [
            p
            for p in products
            if p.get("verification")
            and p["verification"].get("status") == verification_status
        ]

    if seller_id:
        products = [p for p in products if p.get("seller_id") == seller_id]

    return JsonResponse(
        {
            "meta": {
                "count": len(products),
            },
            "data": products,
        }
    )


def get_product_by_id(request, id):
    products = _get_all_product_dicts()
    product = next((p for p in products if p.get("product_id") == str(id)), None)

    if product is None:
        return _product_not_found_response()

    return JsonResponse(
        {
            "meta": {},
            "data": product,
        }
    )


def isCertified(request, id):
    products = _get_all_product_dicts()
    product = next((p for p in products if p.get("product_id") == str(id)), None)

    if product is None:
        return _product_not_found_response()

    verification = product.get("verification")
    certified = bool(verification and verification.get("status") == "verified")

    return JsonResponse(
        {
            "meta": {},
            "data": {
                "product_id": product["product_id"],
                "certification": certified,
                "verification": verification,
            },
            "certification": certified,
        }
    )


def get_sellers(request):
    try:
        if not Seller.objects.exists():
            sync_data_from_files()
        sellers = [seller.to_dict() for seller in Seller.objects.all()]
    except (OperationalError, ProgrammingError):
        sellers = load_raw_sellers()

    return JsonResponse(
        {
            "meta": {
                "count": len(sellers),
            },
            "data": sellers,
        }
    )


def get_verification_partners(request):
    try:
        if not VerificationPartner.objects.exists():
            sync_data_from_files()
        partners = [
            partner.to_dict() for partner in VerificationPartner.objects.all()
        ]
    except (OperationalError, ProgrammingError):
        partners = load_raw_verification_partners()

    return JsonResponse(
        {
            "meta": {
                "count": len(partners),
            },
            "data": partners,
        }
    )


@csrf_exempt
def upload_verification_document(request, id=None):
    """
    Receive a verification_document file (and optional product details) via POST.
    - Fills Product with product details if provided.
    - Stores verification_document on ProductVerification.
    - The document is only visible in Django Admin and is never exposed in API responses.
    """
    if request.method != "POST":
        return JsonResponse(
            {
                "success": False,
                "meta": {},
                "error": {
                    "code": "METHOD_NOT_ALLOWED",
                    "message": "Hanya method POST yang diizinkan untuk mengunggah dokumen",
                },
            },
            status=405,
        )

    if not _authorized_writer(request):
        return _unauthorized_writer_response()

    uploaded_file = (
        request.FILES.get("verification_document")
        or request.FILES.get("document")
        or request.FILES.get("file")
    )
    if not uploaded_file:
        return JsonResponse(
            {
                "success": False,
                "meta": {},
                "error": {
                    "code": "MISSING_DOCUMENT",
                    "message": "File 'verification_document' wajib diunggah melalui multipart/form-data",
                },
            },
            status=400,
        )

    if not Product.objects.exists():
        sync_data_from_files()

    payload = _extract_product_payload(request)
    product_id = str(id or payload.get("product_id") or "").strip()
    verification_id = str(payload.get("verification_id") or "").strip()

    if payload.get("name"):
        product_obj, verification_obj, error_info = _create_or_update_product_submission(
            payload,
            uploaded_file=uploaded_file,
            explicit_product_id=product_id or None,
        )
        if error_info:
            code, message, status_code = error_info
            return JsonResponse(
                {
                    "success": False,
                    "meta": {},
                    "error": {
                        "code": code,
                        "message": message,
                    },
                },
                status=status_code,
            )
        return JsonResponse(
            {
                "success": True,
                "message": "Produk dan dokumen verifikasi berhasil disimpan.",
                "meta": {},
                "data": product_obj.to_dict(),
            },
            status=201,
        )

    verification_obj = None
    if product_id:
        verification_obj = ProductVerification.objects.filter(
            product_id=product_id
        ).first()
        if verification_obj is None:
            product_obj = Product.objects.filter(pk=product_id).first()
            if product_obj is not None:
                verification_obj = ProductVerification(
                    product=product_obj,
                    status=VerificationStatus.PENDING,
                )
    elif verification_id:
        verification_obj = ProductVerification.objects.filter(
            verification_id=verification_id
        ).first()

    if verification_obj is None:
        return JsonResponse(
            {
                "success": False,
                "meta": {},
                "error": {
                    "code": "PRODUCT_NOT_FOUND",
                    "message": "Data verifikasi produk tidak ditemukan",
                },
            },
            status=404,
        )

    verification_obj.verification_document = uploaded_file
    verification_obj.save()

    return JsonResponse(
        {
            "success": True,
            "message": "Dokumen verifikasi berhasil diunggah.",
            "meta": {},
            "data": {
                "product_id": verification_obj.product_id,
                "verification_id": verification_obj.verification_id,
                "status": verification_obj.status,
            },
        },
        status=201,
    )
