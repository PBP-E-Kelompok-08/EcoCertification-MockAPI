import tempfile
from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Product, ProductVerification, Seller, VerificationPartner


class ReadOnlyDRFAPITest(TestCase):
    def setUp(self):
        self.seller = Seller.objects.create(
            seller_id="sel-test",
            name="Toko Test",
            origin="Bandung",
        )
        self.partner = VerificationPartner.objects.create(
            partner_id="partner-test",
            name="Lab Test",
        )
        self.verified_product = Product.objects.create(
            product_id="prd-test-verified",
            name="Tas Daur Ulang",
            seller=self.seller,
            materials=["plastik daur ulang"],
            origin="Bandung",
            eco_features=["recycled", "reusable"],
        )
        ProductVerification.objects.create(
            verification_id="ver-test-verified",
            product=self.verified_product,
            status="verified",
            partner=self.partner,
            tested_at=date(2026, 1, 1),
            valid_until=date(2027, 1, 1),
            eco_score=92.5,
            summary="Lolos verifikasi",
        )
        self.pending_product = Product.objects.create(
            product_id="prd-test-pending",
            name="Botol Pakai Ulang",
            seller=self.seller,
            materials=["stainless steel"],
            origin="Jakarta",
            eco_features=["reusable"],
        )
        ProductVerification.objects.create(
            verification_id="ver-test-pending",
            product=self.pending_product,
            status="pending",
        )

    def test_product_list_memakai_serializer_dan_tidak_mengekspos_dokumen(self):
        response = self.client.get(reverse("main_api:products"))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["meta"]["count"], 2)
        self.assertNotIn("verification_document", data["data"][0]["verification"])

    def test_product_list_dapat_difilter(self):
        response = self.client.get(
            reverse("main_api:products"),
            {"eco_feature": "recycled", "verification_status": "verified"},
        )

        data = response.json()
        self.assertEqual(data["meta"]["count"], 1)
        self.assertEqual(data["data"][0]["product_id"], self.verified_product.pk)

    def test_product_detail(self):
        response = self.client.get(
            reverse("main_api:product-detail", args=[self.verified_product.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["name"], "Tas Daur Ulang")

    def test_product_detail_tidak_ditemukan(self):
        response = self.client.get(
            reverse("main_api:product-detail", args=["tidak-ada"])
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "PRODUCT_NOT_FOUND")

    def test_certification_verified(self):
        response = self.client.get(
            reverse("main_api:product-certification", args=[self.verified_product.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["data"]["certification"])

    def test_certification_pending(self):
        response = self.client.get(
            reverse("main_api:product-certification", args=[self.pending_product.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["data"]["certification"])

    def test_seller_list(self):
        response = self.client.get(reverse("main_api:sellers"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"][0]["seller_id"], self.seller.pk)

    def test_verification_partner_list(self):
        response = self.client.get(reverse("main_api:verification-partners"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"][0]["partner_id"], self.partner.pk)


@override_settings(MOCK_API_WRITE_TOKEN="test-shared-key")
class ProductSubmissionDRFAPITest(TestCase):
    endpoint = "/api/v1/products/"

    def test_post_memerlukan_api_key(self):
        response = self.client.post(
            self.endpoint,
            {"name": "Tas Uji"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "UNAUTHORIZED")

    def test_post_membuat_produk_dengan_status_pending(self):
        response = self.client.post(
            self.endpoint,
            {
                "product_id": "prd-drf-test",
                "name": "Tas Daur Ulang",
                "seller_id": "sel-drf-test",
                "seller_name": "Toko Lestari",
                "origin": "Bandung",
                "materials": ["plastik daur ulang"],
                "eco_features": ["recycled", "reusable"],
            },
            content_type="application/json",
            HTTP_X_MOCK_API_KEY="test-shared-key",
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()["data"]
        self.assertEqual(data["product_id"], "prd-drf-test")
        self.assertEqual(data["verification"]["status"], "pending")
        self.assertNotIn("verification_document", data["verification"])
        self.assertTrue(Product.objects.filter(pk="prd-drf-test").exists())

    def test_post_menolak_payload_tanpa_nama(self):
        response = self.client.post(
            self.endpoint,
            {"seller_id": "sel-drf-test"},
            content_type="application/json",
            HTTP_X_MOCK_API_KEY="test-shared-key",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "VALIDATION_ERROR")
        self.assertIn("name", response.json()["error"]["details"])

    def test_post_menyimpan_dokumen_tanpa_mengeksposnya(self):
        with tempfile.TemporaryDirectory() as media_root:
            document = SimpleUploadedFile(
                "hasil-uji.pdf",
                b"dokumen uji",
                content_type="application/pdf",
            )
            with override_settings(MEDIA_ROOT=media_root):
                response = self.client.post(
                    self.endpoint,
                    {
                        "product_id": "prd-drf-document",
                        "name": "Produk Berdokumen",
                        "verification_document": document,
                    },
                    HTTP_X_MOCK_API_KEY="test-shared-key",
                )

                self.assertEqual(response.status_code, 201)
                product = Product.objects.get(pk="prd-drf-document")
                self.assertTrue(product.verification.verification_document.name)
                self.assertNotIn(
                    "verification_document",
                    response.json()["data"]["verification"],
                )


@override_settings(MOCK_API_WRITE_TOKEN="test-shared-key")
class ProductUpdateDRFAPITest(TestCase):
    def setUp(self):
        self.seller = Seller.objects.create(
            seller_id="sel-update",
            name="Seller Awal",
            origin="Bogor",
        )
        self.product = Product.objects.create(
            product_id="prd-update",
            name="Nama Awal",
            seller=self.seller,
            materials=["kayu"],
            origin="Bogor",
            eco_features=["reusable"],
        )
        ProductVerification.objects.create(
            verification_id="ver-update",
            product=self.product,
            status="verified",
        )
        self.endpoint = reverse("main_api:product-detail", args=[self.product.pk])

    def test_patch_memerlukan_api_key(self):
        response = self.client.patch(
            self.endpoint,
            {"name": "Nama Baru"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "UNAUTHORIZED")

    def test_patch_hanya_memperbarui_field_yang_dikirim(self):
        response = self.client.patch(
            self.endpoint,
            {"name": "Nama Baru", "origin": "Bandung"},
            content_type="application/json",
            HTTP_X_MOCK_API_KEY="test-shared-key",
        )

        self.assertEqual(response.status_code, 200)
        self.product.refresh_from_db()
        self.product.verification.refresh_from_db()
        self.assertEqual(self.product.name, "Nama Baru")
        self.assertEqual(self.product.origin, "Bandung")
        self.assertEqual(self.product.materials, ["kayu"])
        self.assertEqual(self.product.verification.status, "verified")

    def test_put_memerlukan_nama(self):
        response = self.client.put(
            self.endpoint,
            {"origin": "Bandung"},
            content_type="application/json",
            HTTP_X_MOCK_API_KEY="test-shared-key",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("name", response.json()["error"]["details"])

    def test_patch_produk_tidak_ditemukan(self):
        response = self.client.patch(
            reverse("main_api:product-detail", args=["tidak-ada"]),
            {"name": "Nama Baru"},
            content_type="application/json",
            HTTP_X_MOCK_API_KEY="test-shared-key",
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "PRODUCT_NOT_FOUND")


@override_settings(MOCK_API_WRITE_TOKEN="test-shared-key")
class ProductDeleteDRFAPITest(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            product_id="prd-delete",
            name="Produk Hapus",
            materials=[],
            eco_features=[],
        )
        self.verification = ProductVerification.objects.create(
            verification_id="ver-delete",
            product=self.product,
            status="pending",
        )
        self.endpoint = reverse("main_api:product-detail", args=[self.product.pk])

    def test_delete_memerlukan_api_key(self):
        response = self.client.delete(self.endpoint)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "UNAUTHORIZED")
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())

    def test_delete_menghapus_produk_dan_verifikasi(self):
        response = self.client.delete(
            self.endpoint,
            HTTP_X_MOCK_API_KEY="test-shared-key",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["product_id"], self.product.pk)
        self.assertFalse(Product.objects.filter(pk=self.product.pk).exists())
        self.assertFalse(
            ProductVerification.objects.filter(pk=self.verification.pk).exists()
        )

    def test_delete_produk_tidak_ditemukan(self):
        response = self.client.delete(
            reverse("main_api:product-detail", args=["tidak-ada"]),
            HTTP_X_MOCK_API_KEY="test-shared-key",
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "PRODUCT_NOT_FOUND")


@override_settings(MOCK_API_WRITE_TOKEN="test-shared-key")
class VerificationDocumentUploadDRFAPITest(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            product_id="prd-document",
            name="Produk Dokumen",
            materials=[],
            eco_features=[],
        )
        self.verification = ProductVerification.objects.create(
            verification_id="ver-document",
            product=self.product,
            status="pending",
        )
        self.product_endpoint = reverse(
            "main_api:product-document",
            args=[self.product.pk],
        )

    def _document(self):
        return SimpleUploadedFile(
            "hasil-uji.pdf",
            b"dokumen uji",
            content_type="application/pdf",
        )

    def test_upload_memerlukan_api_key(self):
        response = self.client.post(
            self.product_endpoint,
            {"verification_document": self._document()},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "UNAUTHORIZED")

    def test_upload_memerlukan_dokumen(self):
        response = self.client.post(
            self.product_endpoint,
            {},
            HTTP_X_MOCK_API_KEY="test-shared-key",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "MISSING_DOCUMENT")

    def test_upload_berdasarkan_product_id(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                response = self.client.post(
                    self.product_endpoint,
                    {"verification_document": self._document()},
                    HTTP_X_MOCK_API_KEY="test-shared-key",
                )

                self.assertEqual(response.status_code, 201)
                self.verification.refresh_from_db()
                self.assertTrue(self.verification.verification_document.name)
                self.assertNotIn("verification_document", response.json()["data"])

    def test_upload_berdasarkan_verification_id(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                response = self.client.post(
                    reverse("main_api:verification-document"),
                    {
                        "verification_id": self.verification.pk,
                        "file": self._document(),
                    },
                    HTTP_X_MOCK_API_KEY="test-shared-key",
                )

                self.assertEqual(response.status_code, 201)
                self.assertEqual(
                    response.json()["data"]["verification_id"],
                    self.verification.pk,
                )

    def test_upload_produk_tidak_ditemukan(self):
        response = self.client.post(
            reverse("main_api:product-document", args=["tidak-ada"]),
            {"document": self._document()},
            HTTP_X_MOCK_API_KEY="test-shared-key",
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "PRODUCT_NOT_FOUND")
