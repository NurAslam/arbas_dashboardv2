# ARBAS BEHAVIOR ANALYTICS — PPT MATERIAL
## Penjelasan per Tab & Metodologi Perhitungan

---

## 📌 OVERVIEW DASHBOARD

**Tujuan:** Menganalisis perilaku outlet/toko dalam hal pola belanja, loyalitas, dan distribusi pasar — **TANPA focus revenue**.

**Periode Data:** Maret – April 2026
**Total Outlet:** 324 outlets
**Total Transaksi:** 523 transaksi
**Total Channel:** ~11 channel
**Total Area:** 19 area

---

## 📌 SLIDE 1 — METODOLOGI & STRUKTUR DATA

### Sumber Data
| File | Isi |
|------|-----|
| `master_sales_analysis.csv` | 523 transaksi × 33 kolom (bill, customer, product, qty, payment, dll) |
| `customers.csv` | 4.225 outlet × 22 kolom (termasuk geom/wilayah) |

### Join Key
- `customers.csv` kolom `id` ↔ `master_sales_analysis.csv` kolom `customer_id`
- **Match rate:** 100% (324/324 outlets)
- **Transaksi ter-cover:** 349/523 (66.7%)

### Kolom Kunci yang Digunakan
```
customer_id          → ID unik outlet
customer_name        → Nama toko/outlet
customer_channel     → Tipe channel (TOKO, APOTIK, LAINNYA, dll)
customer_city_prov   → Lokasi (kota + provinsi)
product_name         → Nama produk
quantity             → Jumlah unit per transaksi
bill_no              → Nomor transaksi
transaction_date     → Tanggal transaksi
salesman_name        → Nama salesman
payment_type         → CASH / CREDIT / TRANSFER
delivery_status      → DELIVERED / PENDING / dll
geom                 → Koordinat lat/lon (dari customers.csv)
```

---

## 📌 SLIDE 2 — OUTLET BEHAVIOR

### 2.1 Transaction Frequency Distribution

**Pertanyaan:** *"Seberapa sering outlet melakukan transaksi?"*

**Perhitungan:**
```
num_trx = COUNT(bill_no) per customer_id
```

**Pengelompokan:**
| Group | Batas |
|-------|-------|
| 1x | num_trx = 1 |
| 2x | num_trx = 2 |
| 3-4x | 3 ≤ num_trx ≤ 4 |
| 5-9x | 5 ≤ num_trx ≤ 9 |
| 10x+ | num_trx ≥ 10 |

**Formula:**
```
Frequency Distribution = COUNT(outlet) untuk setiap freq_group
```

**Output:** Bar chart vertikal (sumbu X = grup frekuensi, sumbu Y = jumlah outlet)

---

### 2.2 Quantity per Transaction

**Pertanyaan:** *"Setiap transaksi biasanya membeli berapa unit?"*

**Perhitungan:**
```
qty_group = pd.cut(quantity, bins=[1,3,5,10,20,50,1000],
                   labels=['1-2','3-4','5-9','10-19','20-49','50+'])
Qty Distribution = COUNT(transaksi) per qty_group
```

**Formula tambahan:**
```
Mean Qty   = SUM(quantity) / COUNT(bill_no)
Median Qty = MEDIAN(quantity)
Min Qty    = MIN(quantity)
Max Qty    = MAX(quantity)
```

**Output:** Bar chart distribusi quantity per transaksi

---

### 2.3 Recency Distribution

**Pertanyaan:** *"Sudah berapa hari sejak outlet terakhir kali bertransaksi?"*

**Perhitungan:**
```
days_since_last = (Tanggal Data Terakhir) - (Tanggal Transaksi Terakhir per outlet)

Contoh:
- Tanggal data terakhir    = 2026-04-16
- Outlet terakhir transaksi = 2026-04-02
- days_since_last          = 16 - 2 = 14 hari
```

**Pengelompokan (bucket):**
| Group | Batas (hari) | Status |
|-------|-------------|--------|
| 0-3 days | 0–3 | 🟢 Aktif |
| 4-7 days | 4–7 | 🟢 Aktif |
| 8-14 days | 8–14 | 🟡 Warning |
| 15-30 days | 15–30 | 🔴 At Risk |
| 30+ days | >30 | 🔴 Churned |

**Formula:**
```
Churn Rate = COUNT(outlet WHERE days_since_last > 14) / COUNT(all outlet) × 100%
```

**Output:** Bar chart horizontal (warna hijau→merah berdasarkan risiko)

---

### 2.4 Purchase Interval (Repeat Buyers)

**Pertanyaan:** *"Rata-rata berapa hari outlet kembali melakukan pembelian?"*

**Perhitungan:**
```
1. Kelompokkan transaksi per outlet
2. Urutkan transaksi berdasarkan tanggal
3. Hitung selisih antar tanggal berurutan
4. Rata-ratakan selisih tersebut

Contoh:
Outlet ABC transaksi: 2026-03-01, 2026-03-05, 2026-03-10, 2026-03-18
Diffs = [4, 5, 8] → Mean = (4+5+8)/3 = 5.7 hari
```

**Formula:**
```
repeat_interval = RATA-RATA(tanggal[i+1] - tanggal[i]) untuk setiap outlet
```

**Pengelompokan:**
| Group | Batas (hari) |
|-------|-------------|
| Daily | 0–1 |
| 2-3 days | 2–3 |
| 4-5 days | 4–5 |
| 6-7 days | 6–7 |
| 8-14 days | 8–14 |
| 14+ days | >14 |

**Output:** Bar chart distribusi interval repeat

---

### 2.5 Product Preference per Outlet

**Pertanyaan:** *"Produk apa yang paling sering dibeli per outlet?"*

**Perhitungan:**
```
1. Agregasi quantity per customer_id × product_name
2. Ambil produk dengan quantity tertinggi per outlet (mode)

Primary Product = product_name dengan MAX(SUM(quantity)) per customer_id
```

**Formula:**
```
Multi-Product Rate = COUNT(outlet WHERE num_products > 1) / COUNT(all outlet) × 100%
```

---

## 📌 SLIDE 3 — CHANNEL BEHAVIOR

### 3.1 Transactions by Channel

**Pertanyaan:** *"Channel mana yang paling banyak transaksinya?"*

**Perhitungan:**
```
Channel Metrics:
  trx           = COUNT(bill_no) per customer_channel
  outlets       = COUNT(DISTINCT customer_id) per customer_channel
  qty           = SUM(quantity) per customer_channel
  products      = COUNT(DISTINCT product_name) per customer_channel
  trx_per_outlet = trx / outlets
  pct_outlets   = outlets / total_outlets × 100%
```

**Output:** Bar chart transaksi per channel + tabel ringkasan

---

### 3.2 Channel Drill-Down

**Pertanyaan:** *"Di dalam satu channel, outlet mana saja yang ada? Produk apa? Quantity berapa?"*

**Perhitungan per channel yang dipilih:**
```
Outlet Detail:
  num_trx    = COUNT(bill_no) per customer_id
  total_qty  = SUM(quantity) per customer_id
  produk     = DISTINCT product_name (di-join dengan koma)
  salesman   = MODE(salesman_name) per customer_id

Product Breakdown:
  outlets    = COUNT(DISTINCT customer_id) per product_name
  trx        = COUNT(bill_no) per product_name
  total_qty  = SUM(quantity) per product_name
```

---

### 3.3 Delivery Success Rate by Channel

**Pertanyaan:** *"Berapa % transaksi berhasil delivered per channel?"*

**Perhitungan:**
```
1. Crosstab: CHANNEL × delivery_status (DELIVERED / PENDING / dll)

delivered_pct = COUNT(trx WHERE delivery_status = 'DELIVERED') /
                 COUNT(all trx in channel) × 100%

Contoh:
  TOKO channel: 80 delivered / 100 total = 80.0%
```

**Output:** Horizontal bar chart (% delivered) + tabel

---

### 3.4 Payment Behavior by Channel

**Pertanyaan:** *"Metode pembayaran apa yang dominan di setiap channel?"*

**Perhitungan:**
```
1. Crosstab: CHANNEL × payment_type

Crosstab = pd.crosstab(df['customer_channel'], df['payment_type'])
Payment % = (crosstab / baris_sum) × 100  (normalize='index')
```

**Output:** Stacked bar chart (% CASH/CREDIT/TRANSFER per channel)

---

## 📌 SLIDE 4 — MARKET GEOGRAPHY

### 4.1 Outlets by Area

**Pertanyaan:** *"Area mana yang memiliki outlet paling banyak?"*

**Perhitungan:**
```
Area Metrics:
  outlets       = COUNT(DISTINCT customer_id) per city_prov
  trx           = COUNT(bill_no) per city_prov
  channels      = COUNT(DISTINCT customer_channel) per city_prov
  qty           = SUM(quantity) per city_prov
  trx_per_outlet = trx / outlets
  pct_outlets   = outlets / total_outlets × 100%
```

**Output:** Bar chart + tabel detail outlet per area

---

### 4.2 Area × Channel Distribution

**Pertanyaan:** *"Channel apa yang mendominasi di setiap area?"*

**Perhitungan:**
```
area_chan = pd.crosstab(df['city_prov'], df['customer_channel'])

Dominant Channel per Area:
  for each area:
    top_channel = customer_channel dengan MAX(COUNT(transaksi)) di area tersebut
    share = max_count / total_count_area × 100%
```

**Output:** Stacked bar chart + crosstab table

---

### 4.3 Outlet Map (Peta Interaktif)

**Pertanyaan:** *"Di mana lokasi outlets secara geografis?"*

**Perhitungan — Decode Koordinat dari WKB Geometry:**

```
1. Data mentah dari customers.csv kolom 'geom':
   Contoh: 0101000020E6100000EBQ4... (PostGIS WKB hex string)

2. Struktur WKB SRID=4326:
   Bytes 0-8   : byte-order + type + SRID
   Bytes 9-16   : X (longitude) — 8 bytes little-endian double
   Bytes 17-24  : Y (latitude)  — 8 bytes little-endian double

3. Decode dengan Python struct:
   data = bytes.fromhex(hex_string[:50])
   lon = struct.unpack('<d', data[9:17])[0]   # X = longitude
   lat = struct.unpack('<d', data[17:25])[0]  # Y = latitude

4. Validasi range Yogyakarta:
   -9 < lat < -6.5  DAN  109 < lon < 111
```

**Join dengan transaksi:**
```
merged = transactions.merge(
    geo_df[['customer_id','lat','lon','alamat','kota','tipeChannel']],
    on='customer_id', how='left'
)
```

**Output:** Folium map (CartoDB dark tiles) dengan:
- Marker per outlet
- Popup: nama, channel, alamat, transaksi, qty, salesman, lat/lon
- Filter warna: Channel / Kota/Kab / Provinsi / Salesman / Jumlah Trx

---

## 📌 SLIDE 5 — MARKET-SALES PATTERNS

### 5.1 Salesman Coverage

**Pertanyaan:** *"Salesman mana yang mengurusi outlet terbanyak?"*

**Perhitungan:**
```
Salesman Metrics:
  outlets       = COUNT(DISTINCT customer_id) per salesman_name
  trx           = COUNT(bill_no) per salesman_name
  channels      = COUNT(DISTINCT customer_channel) per salesman_name
  areas         = COUNT(DISTINCT city_prov) per salesman_name
  trx_per_outlet = trx / outlets
  pct_outlets   = outlets / total_outlets × 100%
```

**Overlapping Outlet:**
```
overlap = COUNT(customer_id WHERE COUNT(DISTINCT salesman_name) > 1)
```
> Jika 1 outlet ditangani oleh 2+ salesman → territory conflict

**Output:** Bar chart + heatmap salesman × channel/area

---

### 5.2 Heatmap Salesman × Channel / Area

**Perhitungan:**
```
heatmap = pivot_table(
    data = df,
    index = salesman_name,
    columns = customer_channel / city_prov,
    values = bill_no,
    aggfunc = 'count',
    fill_value = 0
)
```

**Output:** Plotly heatmap dengan:
- Sumbu X = Channel / Area
- Sumbu Y = Salesman
- Warna = Jumlah transaksi (semakin gelap = semakin banyak)

---

## 📌 SLIDE 6 — REPEAT ORDER ANALYTICS

### 6.1 Konsep Dasar Repeat Buyer

```
is_repeat = TRUE  jika num_trx > 1
is_repeat = FALSE jika num_trx = 1 (one-time buyer)

repeat_interval = (last_trx - first_trx) / (num_trx - 1)

Contoh:
  Outlet ABC: 5 transaksi dalam 20 hari
  repeat_interval = 20 / (5-1) = 5.0 hari
```

---

### 6.2 Repeat Rate by Channel / Area

**Perhitungan:**
```
repeat_rate_by_channel = COUNT(customer_id WHERE is_repeat = TRUE) /
                          COUNT(all customer_id) per channel × 100%

Contoh:
  TOKO channel: 15 repeat / 40 total = 37.5%
  APOTIK channel: 30 repeat / 50 total = 60.0%
```

**Output:** Bar chart repeat rate + garis rata-rata (dashed line)

---

### 6.3 Repeat Interval Distribution

**Pertanyaan:** *"Seberapa cepat repeat buyers kembali?"*

**Perhitungan:**
```
1. Ambil only repeat buyers (is_repeat = TRUE)
2. Hitung repeat_interval per outlet
3. Kelompokkan dalam bins:

repeat_interval_dist = pd.cut(
    repeat_interval,
    bins=[0, 1, 3, 5, 7, 14, 999],
    labels=['Daily','2-3d','4-5d','6-7d','8-14d','14+d']
)
Distribution = COUNT(outlet) per interval_group
```

**Output:** Pie chart + tabel distribusi

---

### 6.4 Recency of Repeat Customers

**Pertanyaan:** *"Saat ini, repeat buyers masih aktif atau sudah churn?"*

**Perhitungan:**
```
days_since_last_repeat = Tanggal_Data_Akhir - Tanggal_Trx_Terakhir

Recency Group = pd.cut(days_since_last_repeat,
                       bins=[0, 3, 7, 14, 30, 999],
                       labels=['0-3d','4-7d','8-14d','15-30d','30+d'])

Distribution = COUNT(outlet) per recency_group
```

**Perbedaan dengan Section 2.3:**
| | Recency (2.3) | Recency of Repeat (6.4) |
|---|---|---|
| Objek | Semua outlet | Hanya repeat buyers |
| Fokus | Overall status | Status repeat buyers specifically |
| Pertanyaan | "Apakah outlet masih hidup?" | "Repeat buyers masih loyal?" |

---

### 6.5 Top Repeat Customers

**Kriteria "Paling Setia":**
```
Sortir: is_repeat = TRUE
Urutan: DESCENDING by num_trx (jumlah transaksi)

Top 20 = 20 outlet dengan num_trx tertinggi di antara repeat buyers
```

**Output:** Tabel dengan:
- customer_id / nama outlet
- Channel
- Area
- Total transaksi
- Avg interval (hari)
- Days since last transaction

---

## 📌 SLIDE 7 — INSIGHTS & ACTIONS (RINGKASAN)

### Key Metrics yang Dihitung:

| Metric | Formula |
|--------|---------|
| Total Outlet | COUNT(DISTINCT customer_id) |
| Repeat Rate | COUNT(is_repeat=TRUE) / COUNT(all) × 100% |
| Churn Rate | COUNT(days_since_last > 14) / COUNT(all) × 100% |
| One-Time Buyer | COUNT(is_repeat=FALSE) |
| Top Channel | customer_channel dengan MAX(COUNT(trx)) |
| Best Repeat Channel | channel dengan MAX(repeat_rate) |
| Worst Repeat Channel | channel dengan MIN(repeat_rate) |
| Overlapping Outlets | COUNT(customer_id WHERE COUNT(DISTINCT salesman) > 1) |
| Multi-Product Rate | COUNT(num_products > 1) / COUNT(all) × 100% |

---

## 📌 SLIDE 8 — PETA & GEOLOKASI

### Metodologi Decode Koordinat (WKB → Lat/Lon)

```
PostGIS WKB Format (SRID 4326 / WGS84):

Offset   Bytes   Content
  0        1     Byte order (0x01 = little-endian)
  1        4     Geometry type (0x01000000 = Point)
  5        4     SRID (0x0000E610 = 4326)
  9        8     X (longitude) — double 64-bit
  17       8     Y (latitude)  — double 64-bit

Total header = 9 bytes, coords = bytes 9-24 (16 bytes)
```

**Python Code:**
```python
import struct

def decode_wkb_geom(wkb_str):
    if pd.isna(wkb_str) or not wkb_str:
        return None, None
    hex_str = wkb_str.strip()
    if hex_str.startswith('0x'):
        hex_str = hex_str[2:]
    data = bytes.fromhex(hex_str[:50])
    lon = struct.unpack('<d', data[9:17])[0]   # X = Longitude
    lat = struct.unpack('<d', data[17:25])[0]   # Y = Latitude
    # Validasi: Yogyakarta bounds
    if -9 < lat < -6.5 and 109 < lon < 111:
        return lat, lon
    return None, None
```

**Validasi Hasil:**
- Total customers dengan geom: 3,957
- Berhasil decode valid: 3,957 (100%)
- Range lat: -7.45° s/d -8.02° (Sleman, Bantul, Yogyakarta)
- Range lon: 110.13° s/d 110.84°
- Outlets dengan geo dalam transaksi: **205 / 324 (63%)**

---

## 📌 STRUKTUR PPT YANG DISARANKAN

| Slide | Judul | Isi Utama |
|-------|-------|----------|
| 1 | Cover | Judul, periode, total outlets |
| 2 | Overview & Metodologi | Struktur data, join key, kolom kunci |
| 3 | Outlet Behavior | Frequency, Qty, Recency, Interval, Product Pref |
| 4 | Channel Behavior | Trx by channel, Drill-down, Delivery, Payment |
| 5 | Market Geography | Area distribution, Channel×Area, Peta |
| 6 | Market-Sales | Salesman coverage, Heatmap |
| 7 | Repeat Order | Repeat rate, Interval, Recency, Top customers |
| 8 | Insights & Actions | Key findings, Recommendations |
| 9 | Geolocation | Metodologi WKB decode, Hasil peta |

---

*Dokumen ini dibuat sebagai bahan referensi untuk presentasi Arbas Market Intelligence — Behavior Analytics Dashboard*