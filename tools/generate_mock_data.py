#!/usr/bin/env python3
"""
Generator + validator dataset awal EcoCertification-MockAPI (60 produk).

Struktur data mengikuti commit terakhir (3677ef7): product_id, name, slug,
seller_id, materials, origin, eco_features, verification{...}. Tidak ada
field category/description/image_path di Mock API.

Pemakaian (dari root repo):
    python tools/generate_mock_data.py            # generate + validasi
    python tools/generate_mock_data.py --check    # validasi file yang ada saja

prd-001..prd-005 dibaca dari file yang sudah ada dan dipertahankan; hanya
eco_score yang dihitung ulang dan reusable prd-005 (pending) diset null.
Tanggal acuan tetap (TODAY) agar hasil deterministik.
"""
import csv
import json
import random
import re
import sys
from collections import Counter
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

TODAY = date(2026, 10, 24)
NEAR_EXPIRY_DAYS = 30

ROOT = Path(__file__).resolve().parent.parent
PRODUCTS_FILE = ROOT / "data" / "products" / "products-dafiq.json"
SELLERS_FILE = ROOT / "data" / "reference" / "sellers.json"
PARTNERS_FILE = ROOT / "data" / "reference" / "verification-partners.json"
CATALOG_CSV = ROOT / "data" / "catalog" / "catalog-main-seed.csv"

ECO_FEATURES = {
    "reusable", "refillable", "recycled_material", "biodegradable", "compostable",
    "plastic_free_packaging", "locally_sourced", "organic_material",
    "energy_efficient", "water_saving",
}
CATEGORIES = ["clothing", "daily_supplies", "home_kitchen", "furniture", "beauty_care"]

# Komposisi target (kategori -> status). V=verified aktif, N=verified hampir
# berakhir (<=30 hari), P=pending, R=rejected, E=expired. Total 60.
PLAN = {
    "clothing":       {"V": 7, "N": 1, "P": 2, "R": 1, "E": 1},
    "daily_supplies": {"V": 7, "N": 1, "P": 2, "R": 1, "E": 1},
    "home_kitchen":   {"V": 7, "N": 1, "P": 1, "R": 2, "E": 1},
    "furniture":      {"V": 7, "N": 1, "P": 1, "R": 1, "E": 2},
    "beauty_care":    {"V": 6, "N": 2, "P": 2, "R": 1, "E": 1},
}

SELLERS = [
    ("sel-001", "Bhumi Karya Bandung", "Bandung, Jawa Barat"),
    ("sel-002", "Lestari Rumah Jogja", "Sleman, DI Yogyakarta"),
    ("sel-003", "Hijau Bersama Surabaya", "Surabaya, Jawa Timur"),
    ("sel-004", "Nusa Daur Semarang", "Semarang, Jawa Tengah"),
    ("sel-005", "Rimba Kriya Jepara", "Jepara, Jawa Tengah"),
    ("sel-006", "Segar Alam Bogor", "Bogor, Jawa Barat"),
    ("sel-007", "Tenun Hijau Lombok", "Lombok Tengah, Nusa Tenggara Barat"),
    ("sel-008", "Anyam Lestari Cirebon", "Cirebon, Jawa Barat"),
    ("sel-009", "Bumi Bening Denpasar", "Denpasar, Bali"),
    ("sel-010", "Kayu Kita Malang", "Malang, Jawa Timur"),
    ("sel-011", "Sahabat Daur Makassar", "Makassar, Sulawesi Selatan"),
    ("sel-012", "Warna Alam Solo", "Surakarta, Jawa Tengah"),
]

# Partner fiktif (vfp-001/002 sudah ada di data lama).
PARTNERS = [
    ("vfp-001", "EcoCheck Indonesia"),
    ("vfp-002", "Lembaga Verifikasi Bhumi"),
    ("vfp-003", "Laboratorium Uji Material Nusantara"),
    ("vfp-004", "Balai Sertifikasi Produk Hijau"),
    ("vfp-005", "Lembaga Verifikasi Klaim Lestari"),
]

# Kategori prd-001..005 (data lama; kategori hanya dipakai generator/validator).
LEGACY_CATEGORY = {
    "prd-001": "daily_supplies", "prd-002": "clothing", "prd-003": "home_kitchen",
    "prd-004": "furniture", "prd-005": "beauty_care",
}
LEGACY_STATUS = {
    "prd-001": "V", "prd-002": "V", "prd-003": "V", "prd-004": "V", "prd-005": "P",
}

# (kategori, nama, materials, eco_features, recycled%, reusable, seller, status, partner, alasan_tolak)
# recycled% hanya bermakna jika 'recycled_material' ada di eco_features (atau hasil ukur pada R).
ITEMS = [
    # ---- clothing (prd-006..016)
    ("clothing", "Kemeja Rami Pewarna Alami", ["rami"], ["organic_material", "biodegradable", "locally_sourced"], None, None, "sel-007", "V", "vfp-004", None),
    ("clothing", "Syal Tenun Lombok Pewarna Alam", ["kapas", "pewarna alam"], ["organic_material", "locally_sourced", "plastic_free_packaging"], None, None, "sel-007", "V", "vfp-002", None),
    ("clothing", "Rok Tenun Ikat Katun Organik", ["katun organik"], ["organic_material", "locally_sourced", "biodegradable"], None, None, "sel-007", "V", "vfp-004", None),
    ("clothing", "Sarung Tenun Katun Alami", ["katun", "pewarna alam"], ["organic_material", "locally_sourced"], None, None, "sel-007", "N", "vfp-001", None),
    ("clothing", "Celana Kulot Linen Organik", ["linen organik"], ["organic_material", "biodegradable", "plastic_free_packaging"], None, None, "sel-007", "P", None, None),
    ("clothing", "Batik Tulis Pewarna Indigo", ["katun primisima", "indigo alami"], ["organic_material", "locally_sourced", "plastic_free_packaging"], None, None, "sel-012", "V", "vfp-002", None),
    ("clothing", "Kain Batik Cap Pewarna Soga", ["katun", "soga alam"], ["organic_material", "locally_sourced", "biodegradable"], None, None, "sel-012", "V", "vfp-004", None),
    ("clothing", "Outer Batik Limbah Perca", ["kain perca batik"], ["recycled_material", "reusable", "locally_sourced"], 65, True, "sel-012", "V", "vfp-003", None),
    ("clothing", "Selendang Ecoprint Daun Jati", ["katun", "daun jati"], ["organic_material", "locally_sourced", "plastic_free_packaging"], None, None, "sel-012", "E", "vfp-001", None),
    ("clothing", "Jaket Denim Upcycle", ["denim bekas"], ["recycled_material", "reusable", "locally_sourced"], 70, True, "sel-004", "P", None, None),
    ("clothing", "Kaos Serat Bambu", ["serat bambu"], ["biodegradable", "organic_material", "plastic_free_packaging"], None, None, "sel-001", "R", "vfp-003",
     "Klaim biodegradable tidak terbukti: uji komposisi menemukan campuran poliester sekitar 30%."),
    # ---- daily_supplies (prd-017..027)
    ("daily_supplies", "Botol Minum Stainless Isi Ulang", ["baja tahan karat"], ["reusable", "refillable", "plastic_free_packaging"], None, True, "sel-003", "V", "vfp-001", None),
    ("daily_supplies", "Sikat Gigi Gagang Bambu", ["bambu"], ["biodegradable", "plastic_free_packaging", "locally_sourced"], None, False, "sel-009", "V", "vfp-004", None),
    ("daily_supplies", "Sedotan Bambu Alami", ["bambu"], ["reusable", "biodegradable", "locally_sourced"], None, True, "sel-001", "V", "vfp-002", None),
    ("daily_supplies", "Tas Belanja Jaring Daur Ulang", ["serat PET daur ulang"], ["recycled_material", "reusable"], 80, True, "sel-004", "V", "vfp-003", None),
    ("daily_supplies", "Dompet Serat Daun Nanas", ["serat daun nanas"], ["biodegradable", "organic_material", "locally_sourced"], None, None, "sel-010", "V", "vfp-004", None),
    ("daily_supplies", "Kantong Belanja Lipat Katun Daur Ulang", ["katun daur ulang"], ["recycled_material", "reusable", "plastic_free_packaging"], 40, True, "sel-001", "V", "vfp-002", None),
    ("daily_supplies", "Gelas Kopi Sekam Padi", ["sekam padi", "resin nabati"], ["biodegradable", "reusable", "locally_sourced"], None, True, "sel-008", "N", "vfp-003", None),
    ("daily_supplies", "Deterjen Bubuk Buah Lerak", ["buah lerak"], ["biodegradable", "plastic_free_packaging", "water_saving"], None, None, "sel-011", "P", None, None),
    ("daily_supplies", "Tas Anyaman Eceng Gondok", ["eceng gondok"], ["biodegradable", "reusable", "locally_sourced"], None, True, "sel-009", "P", None, None),
    ("daily_supplies", "Pembungkus Hadiah Kain Batik", ["katun batik"], ["reusable", "plastic_free_packaging", "locally_sourced"], None, True, "sel-012", "R", "vfp-005",
     "Dokumen pendukung tidak lengkap sehingga klaim tidak dapat diverifikasi."),
    ("daily_supplies", "Sikat Cuci Botol Sabut Kelapa", ["sabut kelapa", "kayu"], ["biodegradable", "plastic_free_packaging", "locally_sourced"], None, None, "sel-004", "E", "vfp-001", None),
    # ---- home_kitchen (prd-028..038)
    ("home_kitchen", "Kotak Makan Stainless Sekat", ["baja tahan karat"], ["reusable", "plastic_free_packaging"], None, True, "sel-002", "V", "vfp-001", None),
    ("home_kitchen", "Talenan Kayu Jati Bekas", ["kayu jati bekas"], ["recycled_material", "reusable", "locally_sourced"], 90, True, "sel-005", "V", "vfp-003", None),
    ("home_kitchen", "Set Sendok Garpu Bambu Travel", ["bambu"], ["reusable", "biodegradable", "locally_sourced"], None, True, "sel-002", "V", "vfp-002", None),
    ("home_kitchen", "Piring Pelepah Pinang Press", ["pelepah pinang"], ["compostable", "biodegradable", "locally_sourced"], None, False, "sel-008", "V", "vfp-004", None),
    ("home_kitchen", "Gelas Kaca Daur Ulang", ["kaca daur ulang"], ["recycled_material", "reusable"], 95, True, "sel-004", "V", "vfp-003", None),
    ("home_kitchen", "Toples Kaca Tutup Bambu", ["kaca", "bambu"], ["reusable", "plastic_free_packaging"], None, True, "sel-010", "V", "vfp-001", None),
    ("home_kitchen", "Keranjang Cuci Rotan", ["rotan"], ["biodegradable", "reusable", "locally_sourced"], None, True, "sel-008", "N", "vfp-002", None),
    ("home_kitchen", "Sabun Cuci Piring Padat Kelapa", ["minyak kelapa", "abu soda"], ["biodegradable", "plastic_free_packaging", "water_saving"], None, False, "sel-010", "P", None, None),
    ("home_kitchen", "Spons Cuci Serat Luffa", ["luffa"], ["compostable", "biodegradable", "plastic_free_packaging"], None, None, "sel-002", "R", "vfp-003",
     "Klaim compostable tidak lolos uji penguraian karena adanya perekat sintetis pada produk."),
    ("home_kitchen", "Lampu Hias Tempurung Kelapa", ["tempurung kelapa", "kabel"], ["energy_efficient", "locally_sourced"], None, None, "sel-011", "R", "vfp-001",
     "Klaim energy_efficient tidak didukung data konsumsi daya yang memadai."),
    ("home_kitchen", "Wadah Bumbu Tanah Liat", ["tanah liat"], ["reusable", "locally_sourced", "plastic_free_packaging"], None, True, "sel-010", "E", "vfp-001", None),
    # ---- furniture (prd-039..049)
    ("furniture", "Kursi Rotan Anyam Natural", ["rotan"], ["biodegradable", "locally_sourced", "reusable"], None, True, "sel-008", "V", "vfp-004", None),
    ("furniture", "Meja Makan Kayu Jati Bongkaran", ["kayu jati bekas"], ["recycled_material", "locally_sourced"], 90, True, "sel-005", "V", "vfp-003", None),
    ("furniture", "Rak Buku Bambu Laminasi", ["bambu laminasi"], ["locally_sourced", "biodegradable"], None, None, "sel-005", "V", "vfp-001", None),
    ("furniture", "Bangku Kayu Palet Daur Ulang", ["kayu palet"], ["recycled_material", "locally_sourced"], 80, True, "sel-004", "V", "vfp-003", None),
    ("furniture", "Lemari Pakaian Kayu Mahoni Lestari", ["kayu mahoni"], ["locally_sourced", "biodegradable"], None, None, "sel-005", "V", "vfp-001", None),
    ("furniture", "Sofa Rotan Bantalan Kapuk", ["rotan", "kapuk"], ["organic_material", "biodegradable", "locally_sourced"], None, None, "sel-009", "V", "vfp-004", None),
    ("furniture", "Meja Kerja Bambu", ["bambu"], ["locally_sourced", "biodegradable"], None, None, "sel-010", "N", "vfp-002", None),
    ("furniture", "Kursi Lipat Ban Bekas", ["ban bekas", "besi"], ["recycled_material", "reusable"], 60, True, "sel-008", "P", None, None),
    ("furniture", "Rak Sepatu Kayu Limbah Mebel", ["kayu limbah mebel"], ["recycled_material", "locally_sourced"], 75, True, "sel-005", "E", "vfp-001", None),
    ("furniture", "Meja Kopi Serbuk Kayu Press", ["serbuk kayu", "resin"], ["recycled_material", "locally_sourced"], 70, None, "sel-011", "E", "vfp-003", None),
    ("furniture", "Kursi HDPE Daur Ulang", ["HDPE daur ulang"], ["recycled_material", "reusable"], 55, True, "sel-011", "R", "vfp-003",
     "Kandungan material daur ulang terukur 55%, tidak sesuai klaim 100%."),
    # ---- beauty_care (prd-050..060)
    ("beauty_care", "Sabun Batang Kelapa Zaitun", ["minyak kelapa", "minyak zaitun"], ["biodegradable", "plastic_free_packaging", "locally_sourced"], None, False, "sel-006", "V", "vfp-004", None),
    ("beauty_care", "Sampo Batang Teh Hijau", ["ekstrak teh hijau", "minyak kelapa"], ["biodegradable", "plastic_free_packaging", "water_saving"], None, False, "sel-006", "V", "vfp-002", None),
    ("beauty_care", "Deodoran Krim Kemasan Kaca", ["minyak kelapa", "tepung sagu", "botol kaca"], ["refillable", "reusable", "plastic_free_packaging"], None, True, "sel-006", "V", "vfp-001", None),
    ("beauty_care", "Lulur Kopi Isi Ulang", ["bubuk kopi", "minyak kelapa"], ["refillable", "organic_material", "locally_sourced"], None, None, "sel-009", "V", "vfp-004", None),
    ("beauty_care", "Pelembap Wajah Botol Kaca", ["lidah buaya", "botol kaca"], ["refillable", "reusable", "organic_material"], None, True, "sel-003", "V", "vfp-005", None),
    ("beauty_care", "Lip Balm Kemasan Bambu", ["lilin lebah", "bambu"], ["biodegradable", "plastic_free_packaging", "locally_sourced"], None, None, "sel-009", "V", "vfp-002", None),
    ("beauty_care", "Minyak Rambut Kemiri Isi Ulang", ["kemiri", "botol kaca"], ["refillable", "locally_sourced"], None, None, "sel-003", "N", "vfp-005", None),
    ("beauty_care", "Sabun Cair Daun Sirih Isi Ulang", ["daun sirih", "HDPE daur ulang"], ["refillable", "recycled_material"], 50, None, "sel-006", "N", "vfp-003", None),
    ("beauty_care", "Bedak Dingin Beras Kemasan Kaleng", ["tepung beras", "kaleng aluminium"], ["reusable", "plastic_free_packaging", "locally_sourced"], None, True, "sel-003", "R", "vfp-005",
     "Klaim plastic_free_packaging tidak sesuai: segel kemasan mengandung plastik sekali pakai."),
    ("beauty_care", "Masker Rambut Alpukat Kemasan Kompos", ["alpukat", "pati singkong"], ["compostable", "biodegradable", "plastic_free_packaging"], None, False, "sel-006", "E", "vfp-005", None),
    ("beauty_care", "Pasta Gigi Tablet Isi Ulang", ["kalsium karbonat", "mint"], ["refillable", "plastic_free_packaging", "water_saving"], None, False, "sel-011", "P", None, None),
]

PHRASE = {
    "reusable": "dapat digunakan berulang kali",
    "refillable": "dapat diisi ulang",
    "recycled_material": "mengandung material daur ulang",
    "biodegradable": "berbahan yang dapat terurai secara biologis",
    "compostable": "dapat dikompos pada kondisi yang ditentukan",
    "plastic_free_packaging": "dikemas tanpa plastik sekali pakai",
    "locally_sourced": "memakai bahan utama dari sumber lokal",
    "organic_material": "menggunakan material organik",
    "energy_efficient": "membantu mengurangi penggunaan energi",
    "water_saving": "membantu mengurangi penggunaan air",
}
BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
         "Agustus", "September", "Oktober", "November", "Desember"]
PENDING_SUMMARIES = [
    "Klaim produk sedang menunggu proses verifikasi.",
    "Dokumen diterima dan menunggu penjadwalan pengujian.",
    "Pengajuan baru masuk; pengujian belum dimulai.",
]
PRICE_RANGE = {  # rupiah, untuk CSV seed main (usulan, bukan data Mock API)
    "clothing": (85_000, 350_000), "daily_supplies": (15_000, 180_000),
    "home_kitchen": (25_000, 250_000), "furniture": (450_000, 2_800_000),
    "beauty_care": (20_000, 150_000),
}


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def eco_score(features, recycled, reusable):
    """min(jumlah eco_features, 5) + recycled% x 0.03 + 2 jika reusable=true."""
    tenths = Decimal(min(len(features), 5)) * 10
    tenths += (Decimal(recycled or 0) * Decimal("0.3")).quantize(Decimal("1"), ROUND_HALF_UP)
    tenths += 20 if reusable is True else 0
    return float(tenths / 10)


def join_id(parts):
    if len(parts) <= 1:
        return "".join(parts)
    return ", ".join(parts[:-1]) + " dan " + parts[-1]


def feature_phrases(features, recycled):
    out = []
    for f in features[:3]:
        if f == "recycled_material" and recycled:
            out.append(f"mengandung {recycled}% material daur ulang")
        else:
            out.append(PHRASE[f])
    return join_id(out)


def tgl_id(d):
    return f"{d.day} {BULAN[d.month - 1]} {d.year}"


def minus_year(d):
    return d.replace(year=d.year - 1)


def plus_year(d):
    return d.replace(year=d.year + 1)


def build_verification(num, status, features, recycled, reusable, partner_id, reason, rng, partners):
    vid = f"ver-{num:03d}"
    partner = {"partner_id": partner_id, "name": partners[partner_id]} if partner_id else None

    if status == "P":
        return {
            "verification_id": vid, "status": "pending", "partner": None,
            "tested_at": None, "valid_until": None, "recycled_material_percent": None,
            "reusable": None, "eco_score": None,
            "summary": PENDING_SUMMARIES[num % len(PENDING_SUMMARIES)],
        }

    if status == "V":
        tested = date(2026, 6, 1) + timedelta(days=rng.randint(0, 135))
        valid = plus_year(tested)
    elif status == "N":
        valid = TODAY + timedelta(days=rng.randint(4, 28))
        tested = minus_year(valid)
    elif status == "E":
        valid = TODAY - timedelta(days=rng.randint(10, 330))
        tested = minus_year(valid)
    else:  # R
        tested = date(2026, 7, 1) + timedelta(days=rng.randint(0, 100))
        valid = None

    has_rec_tag = "recycled_material" in features
    if has_rec_tag:
        rec = recycled
    else:
        rec = 0 if num % 2 == 0 else None
    reuse = True if "reusable" in features else reusable

    phrases = feature_phrases(features, recycled)
    if status == "V":
        summary = f"Hasil uji menunjukkan produk {phrases}."
    elif status == "N":
        summary = f"Hasil uji menunjukkan produk {phrases}. Masa berlaku verifikasi akan segera berakhir."
    elif status == "E":
        summary = (f"Sebelumnya terverifikasi: produk {phrases}. "
                   f"Masa berlaku berakhir pada {tgl_id(valid)} dan perlu diajukan ulang.")
    else:
        summary = reason

    score = eco_score(features, rec, reuse) if status in ("V", "N", "E") else None
    return {
        "verification_id": vid,
        "status": {"V": "verified", "N": "verified", "E": "expired", "R": "rejected"}[status],
        "partner": partner,
        "tested_at": tested.isoformat(),
        "valid_until": valid.isoformat() if valid else None,
        "recycled_material_percent": rec,
        "reusable": reuse,
        "eco_score": score,
        "summary": summary,
    }


def generate():
    partners = dict(PARTNERS)
    sellers = {s[0]: s for s in SELLERS}
    rng = random.Random(2026)

    existing = json.loads(PRODUCTS_FILE.read_text(encoding="utf-8-sig"))
    legacy = {p["product_id"]: p for p in existing if p["product_id"] in LEGACY_CATEGORY}
    assert len(legacy) == 5, "prd-001..005 tidak ditemukan di file produk"

    products = []
    for pid in sorted(legacy):
        p = legacy[pid]
        v = p["verification"]
        if v["status"] == "pending":
            v["reusable"] = None  # belum dinilai (DATA_SCHEMA bagian 3)
            v["eco_score"] = None
        else:
            v["eco_score"] = eco_score(p["eco_features"], v["recycled_material_percent"], v["reusable"])
        products.append(p)

    for i, (cat, name, materials, features, rec, reuse, sel, st, ptn, reason) in enumerate(ITEMS):
        num = 6 + i
        products.append({
            "product_id": f"prd-{num:03d}",
            "name": name,
            "slug": slugify(name),
            "seller_id": sel,
            "materials": materials,
            "origin": sellers[sel][2],
            "eco_features": features,
            "verification": build_verification(num, st, features, rec, reuse, ptn, reason, rng, partners),
        })
    return products


def category_status_of(products):
    """Peta product_id -> (kategori, kode status) berdasarkan tabel + data lama."""
    cat = dict(LEGACY_CATEGORY)
    code = dict(LEGACY_STATUS)
    for i, it in enumerate(ITEMS):
        pid = f"prd-{6 + i:03d}"
        cat[pid], code[pid] = it[0], it[7]
    return cat, code


def validate(products, sellers, partners):
    errors = []
    err = errors.append
    seller_map = {s["seller_id"]: s for s in sellers}
    partner_map = {p["partner_id"]: p for p in partners}
    cat, code = category_status_of(products)

    if len(products) != 60:
        err(f"jumlah produk {len(products)} != 60")
    ids = [p["product_id"] for p in products]
    if ids != [f"prd-{n:03d}" for n in range(1, 61)]:
        err("product_id harus berurutan prd-001..prd-060")
    if len({p["slug"] for p in products}) != len(products):
        err("slug tidak unik")
    if len({p["name"] for p in products}) != len(products):
        err("name tidak unik")

    seen_status = Counter()
    per_cat = Counter()
    per_seller = Counter()
    seller_verified = Counter()
    for p in products:
        pid = p["product_id"]
        v = p["verification"]
        ft = p["eco_features"]
        if not 3 <= len(p["name"]) <= 120:
            err(f"{pid}: panjang name")
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", p["slug"]):
            err(f"{pid}: format slug")
        if p["seller_id"] not in seller_map:
            err(f"{pid}: seller tidak ada")
        elif p["origin"] != seller_map[p["seller_id"]]["origin"]:
            err(f"{pid}: origin != origin seller")
        if not p["materials"]:
            err(f"{pid}: materials kosong")
        if not ft or len(ft) != len(set(ft)) or not set(ft) <= ECO_FEATURES:
            err(f"{pid}: eco_features tidak valid")
        if v["verification_id"] != "ver-" + pid[4:]:
            err(f"{pid}: verification_id tidak sesuai")
        if v["partner"] and v["partner"] != partner_map.get(v["partner"]["partner_id"]):
            err(f"{pid}: partner tidak cocok dengan referensi")

        st = v["status"]
        tested = date.fromisoformat(v["tested_at"]) if v["tested_at"] else None
        valid = date.fromisoformat(v["valid_until"]) if v["valid_until"] else None
        rec = v["recycled_material_percent"]
        if rec is not None and not 0 <= rec <= 100:
            err(f"{pid}: recycled% di luar 0-100")
        if rec and "recycled_material" not in ft:
            err(f"{pid}: recycled% > 0 tanpa tag recycled_material")

        if st == "pending":
            kode = "P"
            for k in ("partner", "tested_at", "valid_until", "recycled_material_percent",
                      "reusable", "eco_score"):
                if v[k] is not None:
                    err(f"{pid}: pending harus {k}=null")
            if not v["summary"]:
                err(f"{pid}: summary kosong")
        else:
            if v["partner"] is None or tested is None:
                err(f"{pid}: {st} harus punya partner dan tested_at")
            if "recycled_material" in ft and not rec:
                err(f"{pid}: tag recycled_material tapi recycled% kosong/0")
            if "reusable" in ft and v["reusable"] is not True:
                err(f"{pid}: tag reusable tapi verification.reusable bukan true")
            if not v["summary"]:
                err(f"{pid}: summary kosong")
            if st == "rejected":
                kode = "R"
                if valid is not None or v["eco_score"] is not None:
                    err(f"{pid}: rejected harus valid_until=null dan eco_score=null")
            else:
                if valid is None or valid <= tested:
                    err(f"{pid}: valid_until harus setelah tested_at")
                want = eco_score(ft, rec, v["reusable"])
                if v["eco_score"] != want:
                    err(f"{pid}: eco_score {v['eco_score']} != rumus {want}")
                if st == "verified":
                    if valid <= TODAY:
                        err(f"{pid}: verified tetapi valid_until sudah lewat")
                    kode = "N" if valid <= TODAY + timedelta(days=NEAR_EXPIRY_DAYS) else "V"
                elif st == "expired":
                    kode = "E"
                    if valid >= TODAY:
                        err(f"{pid}: expired tetapi valid_until belum lewat")
                else:
                    err(f"{pid}: status tidak dikenal {st}")
                    kode = "?"
        if code.get(pid) != kode:
            err(f"{pid}: skenario {code.get(pid)} != hasil {kode}")
        seen_status[kode] += 1
        per_cat[(cat[pid], kode)] += 1
        per_seller[p["seller_id"]] += 1
        if st == "verified":
            seller_verified[p["seller_id"]] += 1

    if dict(seen_status) != {"V": 34, "N": 6, "P": 8, "R": 6, "E": 6}:
        err(f"komposisi status {dict(seen_status)} tidak sesuai 34/6/8/6/6")
    for c in CATEGORIES:
        for k, n in PLAN[c].items():
            if per_cat[(c, k)] != n:
                err(f"{c}/{k}: {per_cat[(c, k)]} != {n}")
    if any(per_seller[s["seller_id"]] != 5 for s in sellers):
        err(f"produk per seller tidak 5: {dict(per_seller)}")
    if seller_verified["sel-011"] != 0:
        err("sel-011 seharusnya tidak punya produk verified")
    return errors, seen_status


def write_outputs(products):
    dump = lambda obj: json.dumps(obj, indent=2, ensure_ascii=False) + "\n"
    PRODUCTS_FILE.write_text(dump(products), encoding="utf-8")
    SELLERS_FILE.write_text(dump([{"seller_id": a, "name": b, "origin": c} for a, b, c in SELLERS]), encoding="utf-8")
    PARTNERS_FILE.write_text(dump([{"partner_id": a, "name": b} for a, b in PARTNERS]), encoding="utf-8")

    # Seed untuk repo main (usulan harga/stok; kategori hanya ada di sisi main).
    cat, _ = category_status_of(products)
    seller_name = {s[0]: s[1] for s in SELLERS}
    prng = random.Random(60)
    CATALOG_CSV.parent.mkdir(parents=True, exist_ok=True)
    with CATALOG_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["slug", "name", "category", "seller_name", "price_idr", "stock"])
        for p in products:
            lo, hi = PRICE_RANGE[cat[p["product_id"]]]
            price = round(prng.randint(lo, hi) / 500) * 500
            w.writerow([p["slug"], p["name"], cat[p["product_id"]], seller_name[p["seller_id"]],
                        price, prng.randint(5, 80)])


def main():
    check_only = "--check" in sys.argv
    if check_only:
        products = json.loads(PRODUCTS_FILE.read_text(encoding="utf-8-sig"))
    else:
        products = generate()
    sellers = [{"seller_id": a, "name": b, "origin": c} for a, b, c in SELLERS] if not check_only \
        else json.loads(SELLERS_FILE.read_text(encoding="utf-8-sig"))
    partners = [{"partner_id": a, "name": b} for a, b in PARTNERS] if not check_only \
        else json.loads(PARTNERS_FILE.read_text(encoding="utf-8-sig"))

    errors, seen = validate(products, sellers, partners)
    if errors:
        print("VALIDASI GAGAL:")
        for e in errors:
            print(" -", e)
        sys.exit(1)
    if not check_only:
        write_outputs(products)
    print(f"OK: {len(products)} produk, {len(sellers)} seller, {len(partners)} partner. "
          f"Status: {dict(seen)} (V=verified aktif, N=hampir berakhir, P=pending, R=rejected, E=expired)")


if __name__ == "__main__":
    main()
