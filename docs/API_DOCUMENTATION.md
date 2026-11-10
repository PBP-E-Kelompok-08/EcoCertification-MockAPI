# BhumiLestari Eco-Certification API

Dokumen ini menjelaskan kontrak API DRF versi 1 untuk integrasi BhumiLestari Web,
backend marketplace, dan aplikasi Flutter.

## Base URL dan versi

| Lingkungan | Base URL |
|---|---|
| Lokal | `http://127.0.0.1:8000/api/v1` |
| PWS | `https://alfarrel-ersya-bhumilestari-mockapi.pws.cs.ui.ac.id/api/v1` |

Endpoint lama di bawah `/api/` tetap tersedia untuk kompatibilitas. Integrasi baru
harus menggunakan `/api/v1/`.

## Keamanan

Operasi baca bersifat publik. Operasi tulis wajib mengirim header berikut:

```http
X-Mock-Api-Key: <shared-secret>
```

Secret berasal dari environment variable `MOCK_API_WRITE_TOKEN`. Jangan pernah
menyimpan secret ini di source code, Git, atau aplikasi Flutter. Secret di dalam APK
dapat diekstrak oleh pengguna.

Arsitektur yang disarankan:

```text
Flutter --autentikasi pengguna--> Backend BhumiLestari
Backend BhumiLestari --X-Mock-Api-Key--> EcoCertification Mock API
```

Flutter boleh mengakses endpoint GET publik secara langsung. POST, PUT, PATCH,
DELETE, dan unggahan dokumen sebaiknya diteruskan oleh backend BhumiLestari.

## Ringkasan endpoint

| Method | Endpoint | Akses | Kegunaan |
|---|---|---|---|
| `GET` | `/products/` | Publik | Daftar dan filter produk |
| `POST` | `/products/` | API key | Membuat produk dan verifikasi `pending` |
| `GET` | `/products/{product_id}/` | Publik | Detail produk |
| `PUT` | `/products/{product_id}/` | API key | Memperbarui produk; `name` wajib |
| `PATCH` | `/products/{product_id}/` | API key | Memperbarui field tertentu |
| `DELETE` | `/products/{product_id}/` | API key | Menghapus produk dan verifikasinya |
| `GET` | `/products/{product_id}/certification/` | Publik | Status sertifikasi produk |
| `POST` | `/products/{product_id}/document/` | API key | Mengunggah dokumen berdasarkan produk |
| `POST` | `/verify/document/` | API key | Mengunggah dokumen berdasarkan produk/verifikasi |
| `GET` | `/verifications/{verification_id}/` | Publik | Detail hasil verifikasi |
| `PUT` | `/verifications/{verification_id}/` | API key | Mengganti hasil verifikasi; `status` wajib |
| `PATCH` | `/verifications/{verification_id}/` | API key | Memperbarui sebagian hasil verifikasi |
| `GET` | `/sellers/` | Publik | Daftar seller referensi |
| `GET` | `/verification-partners/` | Publik | Daftar partner verifikasi |

## Bentuk respons

Respons daftar:

```json
{
  "meta": { "count": 1 },
  "data": []
}
```

Respons detail:

```json
{
  "meta": {},
  "data": {}
}
```

Respons gagal:

```json
{
  "success": false,
  "meta": {},
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Data tidak valid",
    "details": {}
  }
}
```

## Produk

### Daftar produk

```http
GET /api/v1/products/
```

Query parameter opsional:

| Parameter | Contoh | Keterangan |
|---|---|---|
| `eco_feature` | `reusable` | Produk mengandung tag tersebut |
| `verification_status` | `verified` | Status `pending`, `verified`, `rejected`, atau `expired` |
| `status` | `verified` | Alias `verification_status` |
| `seller_id` | `sel-001` | Produk milik seller tertentu |

Contoh:

```http
GET /api/v1/products/?eco_feature=reusable&verification_status=verified
```

### Membuat produk

```http
POST /api/v1/products/
Content-Type: application/json
X-Mock-Api-Key: <shared-secret>
```

```json
{
  "name": "Sedotan Bambu Alami",
  "seller_id": "sel-001",
  "seller_name": "Toko Lestari",
  "materials": ["bambu"],
  "origin": "Bandung, Jawa Barat",
  "eco_features": ["reusable", "biodegradable"]
}
```

Field `product_id` dan `slug` bersifat opsional dan akan dibuat otomatis jika tidak
dikirim. Seller baru akan dibuat jika `seller_id` belum terdaftar. Setiap produk baru
otomatis memperoleh `ProductVerification` dengan status `pending`.

Contoh respons `201 Created`:

```json
{
  "success": true,
  "message": "Produk berhasil disimpan dan menunggu verifikasi admin.",
  "meta": {},
  "data": {
    "product_id": "prd-061",
    "name": "Sedotan Bambu Alami",
    "slug": "sedotan-bambu-alami",
    "seller_id": "sel-001",
    "materials": ["bambu"],
    "origin": "Bandung, Jawa Barat",
    "eco_features": ["reusable", "biodegradable"],
    "verification": {
      "verification_id": "ver-061",
      "status": "pending",
      "partner": null,
      "tested_at": null,
      "valid_until": null,
      "recycled_material_percent": null,
      "reusable": null,
      "eco_score": null,
      "summary": null,
      "certification": false
    }
  }
}
```

### Detail, pembaruan, dan penghapusan

```http
GET /api/v1/products/prd-001/
PATCH /api/v1/products/prd-001/
PUT /api/v1/products/prd-001/
DELETE /api/v1/products/prd-001/
```

Gunakan PATCH untuk memperbarui sebagian field:

```json
{
  "name": "Nama Produk Baru",
  "eco_features": ["reusable", "locally_sourced"]
}
```

Field produk yang dapat diubah adalah `name`, `slug`, `seller_id`, `seller_name`,
`materials`, `origin`, `eco_features`, dan `verification_document`. Status dan hasil
verifikasi tidak dapat diubah melalui endpoint produk.

DELETE juga menghapus objek verifikasi yang terhubung melalui cascade.

## Status sertifikasi

```http
GET /api/v1/products/prd-001/certification/
```

Nilai `certification` dihitung dari `verification.status == "verified"` dan tidak
disimpan sebagai field database terpisah.

```json
{
  "meta": {},
  "data": {
    "product_id": "prd-001",
    "certification": true,
    "verification": {}
  },
  "certification": true
}
```

## Dokumen verifikasi

Dokumen hanya disimpan untuk pemeriksaan admin. Nama file, path, dan URL dokumen
tidak pernah dikirim oleh serializer publik.

Unggah berdasarkan product ID:

```bash
curl -X POST "$BASE_URL/products/prd-001/document/" \
  -H "X-Mock-Api-Key: $MOCK_API_WRITE_TOKEN" \
  -F "verification_document=@./hasil-uji.pdf"
```

Unggah berdasarkan verification ID:

```bash
curl -X POST "$BASE_URL/verify/document/" \
  -H "X-Mock-Api-Key: $MOCK_API_WRITE_TOKEN" \
  -F "verification_id=ver-001" \
  -F "file=@./hasil-uji.pdf"
```

Nama field file yang diterima: `verification_document`, `document`, atau `file`.

## Hasil verifikasi

```http
GET /api/v1/verifications/ver-001/
PATCH /api/v1/verifications/ver-001/
```

Contoh keputusan admin:

```json
{
  "status": "verified",
  "partner_id": "vfp-001",
  "tested_at": "2026-09-01",
  "valid_until": "2027-09-01",
  "recycled_material_percent": 80,
  "reusable": true,
  "eco_score": 7.4,
  "summary": "Lolos kriteria pengujian."
}
```

Aturan validasi:

- `status`: `pending`, `verified`, `rejected`, atau `expired`.
- `partner_id` harus tersedia pada `/verification-partners/`.
- `recycled_material_percent`: 0–100 atau `null`.
- `eco_score`: 0–10 atau `null`.
- `valid_until` tidak boleh lebih awal daripada `tested_at`.
- PUT mewajibkan `status`; PATCH menerima field parsial.

## Kode error utama

| HTTP | Code | Arti |
|---:|---|---|
| 400 | `VALIDATION_ERROR` | Payload tidak memenuhi kontrak |
| 400 | `MISSING_DOCUMENT` | File dokumen belum dikirim |
| 401 | `UNAUTHORIZED` | API key kosong atau tidak cocok |
| 404 | `PRODUCT_NOT_FOUND` | Produk atau data verifikasi produk tidak ditemukan |
| 404 | `VERIFICATION_NOT_FOUND` | Verification ID tidak ditemukan |

## Menjalankan secara lokal

Salin `.env.example`, isi secret lokal, lalu jalankan:

```bash
python manage.py migrate
python manage.py load_mock_data
python manage.py check
python manage.py test
python manage.py runserver
```

Contoh environment:

```env
PRODUCTION=False
DJANGO_SECRET_KEY=local-development-secret
MOCK_API_WRITE_TOKEN=local-shared-write-token
```

## Catatan kompatibilitas `/api/`

Endpoint manual Django lama tetap aktif di bawah `/api/`. Jangan menghapusnya sampai
seluruh consumer lama telah bermigrasi. Pengembangan baru dan aplikasi Flutter harus
mengikuti kontrak `/api/v1/` pada dokumen ini.
