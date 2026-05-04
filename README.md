# Arbas Market Intelligence — Behavior Analytics

Dashboard interaktif untuk menganalisis perilaku outlet, pola channel, geografi pasar, dan repeat order — **tanpa focus revenue**.

![Streamlit](https://img.shields.io/badge/Streamlit-1.42-orange) ![Python](https://img.shields.io/badge/Python-3.9+-blue) ![Plotly](https://img.shields.io/badge/Plotly-5.24-green)

---

## 📌 Overview

Dashboard ini menganalisis **324 outlets** dengan **523 transaksi** dalam periode **Maret – April 2026**. Fokusnya pada:

- 🏠 **Outlet Behavior** — Frekuensi, quantity, recency, purchase interval
- 📊 **Channel Behavior** — Distribusi channel, drill-down per outlet
- 🗺️ **Market Geography** — Area distribution + Peta interaktif (Folium)
- 👤 **Market-Sales** — Coverage salesman, territory analysis
- 🔁 **Repeat Order** — Repeat rate, interval, top loyal customers
- ⏰ **Jam Analisis** — Pola input per jam dari `createdAt` Transaction.csv

---

## 🚀 Quick Start

### 1. Clone repo

```bash
git clone https://github.com/YOUR_USERNAME/arbas-market-intelligence.git
cd arbas-market-intelligence
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run locally

```bash
streamlit run dashboard_behavior.py --server.port=8502
```

Buka browser: **http://localhost:8502**

---

## ☁️ Deploy ke Streamlit Cloud

### Opsi A: Push dari folder `test_data/` (direkomendasikan)

1. Buat **repo baru di GitHub**
2. Copy/push **SEMUA file** dari folder `test_data/` ke root repo:
```
dashboard_behavior.py      ← main app (PASTIKAN ini di root, bukan subfolder!)
master_sales_analysis.csv
customers.csv
Transaction.csv
requirements.txt
README.md
```
3. Buka **[share.streamlit.io](https://share.streamlit.io)**
4. Pilih repo → branch `main` → file `dashboard_behavior.py`
5. Klik **Deploy!**

### Opsi B: Dari repo parent

Pastikan `dashboard_behavior.py` dan semua file CSV ada di **root folder repo**, bukan di subfolder.

> ⚠️ **PENTING:** `dashboard_behavior.py` harus ada di **root** repo, bukan di subfolder, agar Streamlit Cloud bisa menemukan file CSV secara relatif.

---

### File yang perlu di-push:**
```
dashboard_behavior.py      ← main dashboard (WAJIB di root)
master_sales_analysis.csv  ← data transaksi
customers.csv              ← master outlet + geometry
Transaction.csv             ← transaksi + createdAt (untuk jam)
requirements.txt           ← Python dependencies
README.md                  ← dokumentasi
```

---

## 📁 Data Sources

| File | Deskripsi | Rows |
|------|-----------|------|
| `master_sales_analysis.csv` | Data transaksi utama | 523 |
| `customers.csv` | Master outlet + WKB geometry (PostGIS) | 4,225 |
| `Transaction.csv` | Data transaksi + `createdAt` timestamp | 523 |

### Join Keys
- `master_sales_analysis.csv` column `customer_id` ↔ `customers.csv` column `id`
- `master_sales_analysis.csv` column `bill_no` ↔ `Transaction.csv` column `billNo`

---

## 🗺️ Geolocation Feature

Koordinat outlet diambil dari kolom `geom` di `customers.csv` — format **PostGIS WKB hex string**.

```
Example: 0101000020E6100000EBQ4...
```

Decoding:
- Bytes 9-16 → Longitude (little-endian double)
- Bytes 17-24 → Latitude (little-endian double)
- Validasi: Yogyakarta bounds (lat -9 ~ -6.5, lon 109 ~ 111)

**Hasil:** 3,957 outlets berhasil decode, **205 outlets (63%)** dalam transaksi memiliki koordinat.

---

## ⏰ Jam Analysis

Jam transaksi diambil dari kolom `createdAt` di `Transaction.csv` (bukan dari `transaction_date` di master_sales_analysis.csv yang hanya berisi tanggal tanpa jam).

```python
# Ambil jam dari createdAt
tx['createdAt'] = pd.to_datetime(tx['createdAt'])
tx['hour'] = tx['createdAt'].dt.hour
```

---

## 📋 Tab Menu

| Tab | Fokus |
|-----|-------|
| 🏠 Outlet Behavior | Frequency, Qty, Recency, Interval, Product Pref, Jam Analysis |
| 📊 Channel Behavior | Trx by Channel, Drill-Down, Delivery, Payment |
| 🗺️ Market Geography | Area Distribution, Heatmap Area×Jam, Peta Folium |
| 👤 Market-Sales | Salesman Coverage, Heatmap, Territory |
| 🔁 Repeat Order | Repeat Rate, Interval Distribution, Top Customers |
| 💡 Insights | Summary, Key Findings, Recommendations |

---

## 📊 Screenshots

*(Tambahkan screenshot di sini setelah deployment berhasil)*

---

## ⚙️ Tech Stack

- **Python 3.9+**
- **Streamlit** — Web framework
- **Pandas** — Data manipulation
- **Plotly** — Interactive charts
- **Folium + streamlit-folium** — Interactive maps

---

## 📝 License

Internal use only — PT Multimedia Solusi Prima.

---

*Generated: 2026-05-04*