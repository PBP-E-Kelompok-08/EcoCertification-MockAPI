# BhumiLestari Eco-Certification Mock API Documentation

Mock API service for querying eco-certification and submitting seller products and verification documents for the **BhumiLestari** marketplace.

---

## Verification Workflow Overview

1. **Seller -> Marketplace:** The seller submits product details (`name`, `seller_id`, `materials`, `origin`, `eco_features`) along with a supporting verification document (`verification_document`).
2. **Marketplace -> Mock API (`POST`):** The marketplace sends the product details and document to this Mock API:
   - Either in a **single `multipart/form-data` `POST` request** to `/api/products/` (or `/api/verify/document/`), containing the product details (as form fields or a JSON string in `data`/`product`) and the `verification_document` file.
   - Or in **two steps**: a JSON `POST /api/products/` with the product details first, followed by a `multipart/form-data` `POST /api/products/<product_id>/document/` with the file.
3. **Mock API Processing:**
   - Populates the `Product` model with the submitted product details (not the document).
   - Automatically creates a linked `ProductVerification` record with an auto-generated `verification_id` (`ver-NNN`), initial `status: "pending"`, and attaches `verification_document`.
   - `verification_document` is never exposed in any API response.
4. **Mock API Admin Review (`/admin/`):**
   - In Django Admin under **Product verifications**, `verification_id`, `product`, and `verification_document` are **read-only** (locked from modification, while the admin can click `verification_document` to view/download the file).
   - The admin manually fills or updates all other verification fields: `status` (`verified`, `rejected`, `expired`, `pending`), `partner`, `tested_at`, `valid_until`, `recycled_material_percent`, `reusable`, `eco_score`, and `summary`.

---

## Base URL

- **Local Development:** `http://127.0.0.1:8000`
- **Production (PWS):** `https://alfarrel-ersya-bhumilestari-mockapi.pws.cs.ui.ac.id`

---

## Endpoints

### 1. Submit Product & Verification Request (`POST /api/products/`)

Receives product details (and optionally the `verification_document` file) from the marketplace, populates the `Product` model, and creates its initial `ProductVerification` record (`status: "pending"`).

- **URL:** `/api/products/`
- **Method:** `POST`
- **CSRF Exempt:** Yes
- **Content-Type:** `application/json` or `multipart/form-data`

#### Request Fields

| Field | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `name` | `string` | Yes | Product name |
| `product_id` | `string` | No | Optional product ID (`prd-NNN`). Auto-generated if omitted |
| `slug` | `string` | No | Optional URL slug. Auto-generated uniquely from `name` if omitted |
| `seller_id` | `string` | No | Seller ID (`sel-NNN`). Auto-created if not yet in `Seller` table |
| `seller_name` | `string` | No | Optional seller name if creating a new seller |
| `origin` | `string` | No | Product origin location (e.g., `"Bandung, Jawa Barat"`) |
| `materials` | `array<string>` | No | List of materials (or JSON array string / comma-separated string in form-data) |
| `eco_features` | `array<string>` | No | List of eco feature tags (or JSON array string / comma-separated string in form-data) |
| `verification_document` | `file` | No | Optional supporting document file when using `multipart/form-data` (hidden from API responses; visible only in Django Admin) |

#### Example A — JSON `POST` (Product Details Only)

```bash
curl -X POST "http://127.0.0.1:8000/api/products/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sedotan Bambu Alami",
    "seller_id": "sel-001",
    "materials": ["bambu"],
    "origin": "Bandung, Jawa Barat",
    "eco_features": ["reusable", "biodegradable", "locally_sourced"]
  }'
```

#### Example B — Multipart `POST` (JSON Product Details + Document File Together)

```bash
curl -X POST "http://127.0.0.1:8000/api/products/" \
  -F 'data={"name":"Sedotan Bambu Alami","seller_id":"sel-001","materials":["bambu"],"origin":"Bandung, Jawa Barat","eco_features":["reusable","biodegradable"]}' \
  -F "verification_document=@/path/to/document.pdf"
```

#### Example Response (`201 Created`)

```json
{
  "success": true,
  "message": "Produk berhasil disimpan dan menunggu verifikasi admin.",
  "meta": {},
  "data": {
    "product_id": "prd-006",
    "name": "Sedotan Bambu Alami",
    "slug": "sedotan-bambu-alami",
    "seller_id": "sel-001",
    "materials": [
      "bambu"
    ],
    "origin": "Bandung, Jawa Barat",
    "eco_features": [
      "reusable",
      "biodegradable",
      "locally_sourced"
    ],
    "verification": {
      "verification_id": "ver-006",
      "status": "pending",
      "partner": null,
      "tested_at": null,
      "valid_until": null,
      "recycled_material_percent": null,
      "reusable": null,
      "eco_score": null,
      "summary": null
    }
  }
}
```

---

### 2. Upload Verification Document (`POST /api/products/<product_id>/document/`)

Uploads or attaches a `verification_document` file to a product's `ProductVerification` record via `POST` (`multipart/form-data`).
- **Privacy:** The uploaded document is **never** returned or exposed in any API endpoint (`GET /api/products/`, `GET /api/products/<id>/`, etc.). It can **only** be viewed and downloaded inside **Django Admin** by logged-in staff users, where it is locked as read-only.

- **URL:** `/api/products/<product_id>/document/` (or `/api/verify/document/`)
- **Method:** `POST`
- **Content-Type:** `multipart/form-data`

#### Form-Data Fields

| Field | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `verification_document` | `file` | Yes | Document file to upload (aliases `document` or `file` also accepted) |
| `product_id` | `string` | Conditional | Required if calling `/api/verify/document/` for an existing product |
| `verification_id` | `string` | No | Optional alternative identifier (`ver-NNN`) when calling `/api/verify/document/` |
| `data` / product fields | `json` / `string` | No | If product details (`name`, etc.) are also passed here, the `Product` will be created/updated automatically |

#### Example Request

```bash
curl -X POST "http://127.0.0.1:8000/api/products/prd-006/document/" \
  -F "verification_document=@/path/to/document.pdf"
```

#### Example Response (`201 Created`)

```json
{
  "success": true,
  "message": "Dokumen verifikasi berhasil diunggah.",
  "meta": {},
  "data": {
    "product_id": "prd-006",
    "verification_id": "ver-006",
    "status": "pending"
  }
}
```

---

### 3. List Products (`GET /api/products/`)

Retrieves a list of products and their eco-certification details. Supports optional query parameters for filtering.

- **URL:** `/api/products/`
- **Method:** `GET`

#### Query Parameters (Optional)

| Parameter | Type | Description | Example |
| :--- | :--- | :--- | :--- |
| `eco_feature` | `string` | Filter products containing a specific eco feature tag | `?eco_feature=reusable` |
| `verification_status` | `string` | Filter by verification status (`pending`, `verified`, `rejected`, `expired`). Alias: `status` | `?verification_status=verified` |
| `seller_id` | `string` | Filter by seller ID (`sel-NNN`) | `?seller_id=sel-001` |

#### Example Requests

```bash
curl "http://127.0.0.1:8000/api/products/"
curl "http://127.0.0.1:8000/api/products/?eco_feature=reusable&verification_status=verified"
```

#### Example Response (`200 OK`)

```json
{
  "meta": {
    "count": 1
  },
  "data": [
    {
      "product_id": "prd-001",
      "name": "Tas Belanja Katun Pakai Ulang",
      "slug": "tas-belanja-katun-pakai-ulang",
      "seller_id": "sel-001",
      "materials": [
        "katun"
      ],
      "origin": "Bandung, Jawa Barat",
      "eco_features": [
        "reusable",
        "plastic_free_packaging",
        "locally_sourced"
      ],
      "verification": {
        "verification_id": "ver-001",
        "status": "verified",
        "partner": {
          "partner_id": "vfp-001",
          "name": "EcoCheck Indonesia"
        },
        "tested_at": "2026-09-01",
        "valid_until": "2027-09-01",
        "recycled_material_percent": 0,
        "reusable": true,
        "eco_score": null,
        "summary": "Dapat digunakan kembali dan dikemas tanpa plastik sekali pakai."
      }
    }
  ]
}
```

---

### 4. Get Product by ID (`GET /api/products/<product_id>/`)

Retrieves detailed information and verification data for a single product by its `product_id`.

- **URL:** `/api/products/<product_id>/`
- **Method:** `GET`

#### Path Parameters

| Parameter | Type | Description | Example |
| :--- | :--- | :--- | :--- |
| `product_id` | `string` | Unique product identifier (`prd-NNN`) | `prd-001` |

#### Example Request

```bash
curl "http://127.0.0.1:8000/api/products/prd-001/"
```

#### Example Response (`200 OK`)

```json
{
  "meta": {},
  "data": {
    "product_id": "prd-001",
    "name": "Tas Belanja Katun Pakai Ulang",
    "slug": "tas-belanja-katun-pakai-ulang",
    "seller_id": "sel-001",
    "materials": [
      "katun"
    ],
    "origin": "Bandung, Jawa Barat",
    "eco_features": [
      "reusable",
      "plastic_free_packaging",
      "locally_sourced"
    ],
    "verification": {
      "verification_id": "ver-001",
      "status": "verified",
      "partner": {
        "partner_id": "vfp-001",
        "name": "EcoCheck Indonesia"
      },
      "tested_at": "2026-09-01",
      "valid_until": "2027-09-01",
      "recycled_material_percent": 0,
      "reusable": true,
      "eco_score": null,
      "summary": "Dapat digunakan kembali dan dikemas tanpa plastik sekali pakai."
    }
  }
}
```

#### Example Response (`404 Not Found`)

```json
{
  "meta": {},
  "error": {
    "code": "PRODUCT_NOT_FOUND",
    "message": "Produk tidak ditemukan"
  }
}
```

---

### 5. Check Product Certification Status (`GET /api/products/<product_id>/certification/`)

Checks whether a specific product is actively certified (`verification.status == "verified"`) and returns its verification object.

- **URL:** `/api/products/<product_id>/certification/`
- **Method:** `GET`

#### Example Request

```bash
curl "http://127.0.0.1:8000/api/products/prd-001/certification/"
```

#### Example Response (`200 OK`)

```json
{
  "meta": {},
  "data": {
    "product_id": "prd-001",
    "certification": true,
    "verification": {
      "verification_id": "ver-001",
      "status": "verified",
      "partner": {
        "partner_id": "vfp-001",
        "name": "EcoCheck Indonesia"
      },
      "tested_at": "2026-09-01",
      "valid_until": "2027-09-01",
      "recycled_material_percent": 0,
      "reusable": true,
      "eco_score": null,
      "summary": "Dapat digunakan kembali dan dikemas tanpa plastik sekali pakai."
    }
  },
  "certification": true
}
```

---

### 6. List Sellers (`GET /api/sellers/`)

Retrieves the list of reference sellers registered in the dataset.

- **URL:** `/api/sellers/`
- **Method:** `GET`

#### Example Response (`200 OK`)

```json
{
  "meta": {
    "count": 3
  },
  "data": [
    {
      "seller_id": "sel-001",
      "name": "Bhumi Karya Bandung",
      "origin": "Bandung, Jawa Barat"
    },
    {
      "seller_id": "sel-002",
      "name": "Lestari Rumah Jogja",
      "origin": "Sleman, DI Yogyakarta"
    },
    {
      "seller_id": "sel-003",
      "name": "Hijau Bersama Surabaya",
      "origin": "Surabaya, Jawa Timur"
    }
  ]
}
```

---

### 7. List Verification Partners (`GET /api/verification-partners/`)

Retrieves the list of eco-certification / verification partner organizations.

- **URL:** `/api/verification-partners/`
- **Method:** `GET`

#### Example Response (`200 OK`)

```json
{
  "meta": {
    "count": 2
  },
  "data": [
    {
      "partner_id": "vfp-001",
      "name": "EcoCheck Indonesia"
    },
    {
      "partner_id": "vfp-002",
      "name": "Lembaga Verifikasi Bhumi"
    }
  ]
}
```

---

## Enumerations & Valid Values

### Eco Features (`eco_features`)

| Value | Description |
| :--- | :--- |
| `reusable` | Designed to be used repeatedly |
| `refillable` | Container or product can be refilled |
| `recycled_material` | Contains recycled materials |
| `biodegradable` | Material can decompose biologically under appropriate conditions |
| `compostable` | Material can be composted under specified conditions |
| `plastic_free_packaging` | Packaging does not use single-use plastics |
| `locally_sourced` | Primary materials are obtained from local sources |
| `organic_material` | Uses organic materials according to supplier/verifier info |
| `energy_efficient` | Helps reduce energy consumption |
| `water_saving` | Helps reduce water consumption |

### Verification Status (`verification.status`)

| Value | Description | Certified (`certification`) |
| :--- | :--- | :--- |
| `verified` | Passed verification and currently valid | `true` |
| `pending` | Currently awaiting verification | `false` |
| `rejected` | Did not meet verification criteria | `false` |
| `expired` | Previously verified, but `valid_until` has passed | `false` |

---

## Local Setup & Data Synchronization

```bash
# 1. Apply database migrations
python manage.py migrate

# 2. Seed/synchronize data from data/ directory into database
python manage.py load_mock_data

# 3. Run development server
python manage.py runserver
```
