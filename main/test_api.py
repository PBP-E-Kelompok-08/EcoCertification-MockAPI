from datetime import date

from django.test import TestCase
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
