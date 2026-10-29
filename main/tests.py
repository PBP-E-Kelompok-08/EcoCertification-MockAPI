import json

from django.test import TestCase, override_settings
from main.models import Product
from main.views import sync_data_from_files


@override_settings(MOCK_API_WRITE_TOKEN="test-shared-key")
class ProductApiContractTests(TestCase):
    def test_submission_requires_shared_key(self):
        payload = json.dumps({"name": "Tas Uji", "seller_id": "sel-test"})
        response = self.client.post("/api/products/", payload, content_type="application/json")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "UNAUTHORIZED")

        response = self.client.post(
            "/api/products/", payload, content_type="application/json",
            HTTP_X_MOCK_API_KEY="test-shared-key",
        )
        self.assertEqual(response.status_code, 201)
        product_id = response.json()["data"]["product_id"]
        detail = self.client.get(f"/api/products/{product_id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["data"]["verification"]["status"], "pending")
        certification = self.client.get(f"/api/products/{product_id}/certification/")
        self.assertFalse(certification.json()["data"]["certification"])

    def test_document_upload_requires_shared_key(self):
        response = self.client.post("/api/verify/document/")
        self.assertEqual(response.status_code, 401)

    def test_seed_does_not_overwrite_live_verification(self):
        sync_data_from_files()
        product = Product.objects.get(pk="prd-001")
        product.name = "Nama di database PWS"
        product.save(update_fields=["name"])
        verification = product.verification
        verification.status = "rejected"
        verification.summary = "Keputusan admin"
        verification.save(update_fields=["status", "summary"])

        sync_data_from_files()
        product.refresh_from_db()
        verification.refresh_from_db()
        self.assertEqual(product.name, "Nama di database PWS")
        self.assertEqual(verification.status, "rejected")
        self.assertEqual(verification.summary, "Keputusan admin")
