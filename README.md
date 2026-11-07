# SegmenKu — Dashboard Segmentasi Pelanggan (RFM)

Dashboard Streamlit untuk mengelompokkan pelanggan dengan metode **RFM**
(Recency, Frequency, Monetary). Tampilan mengikuti desain Figma SegmenKu.

## Halaman
| Halaman | Isi |
|---|---|
| **Dashboard** | Kartu metrik, distribusi 5 segmen (donat), sebaran recency, pelanggan teratas, unduh hasil (CSV & ZIP) |
| **Unggah Data** | Unggah CSV/Excel, petakan kolom otomatis, pratinjau, lalu analisis ulang |
| **Pelanggan** | Cari ID, filter segmen, urutkan, klik baris untuk membuka detail |
| **Detail Segmen** | Ringkasan segmen, saran tindakan marketing, daftar pelanggan, kartu detail skor R-F-M |

## Struktur folder
```
segmenku-streamlit/
├── app.py                 # aplikasi utama (4 halaman)
├── rfm.py                 # perhitungan skor RFM & aturan segmen
├── components.py          # komponen HTML (kartu, grafik, tabel)
├── requirements.txt
├── assets/
│   ├── segmenku.css       # design token dari Figma
│   ├── streamlit.css      # penyesuaian tampilan Streamlit
│   └── logo.svg
├── data/
│   └── RFM_data.csv       # dataset bawaan (2.194 pelanggan)
└── .streamlit/
    └── config.toml        # tema warna Streamlit
```

## Menjalankan di komputer
```bash
pip install -r requirements.txt
streamlit run app.py
```
Lalu buka http://localhost:8501

## Deploy ke Streamlit Community Cloud
1. Upload seluruh isi folder ini ke repository GitHub (pastikan folder `.streamlit` ikut terunggah).
2. Buka https://share.streamlit.io dan login dengan akun GitHub.
3. Klik **Create app**, pilih repository ini, branch `main`, dan main file `app.py`.
4. Klik **Deploy**.

## Cara skoring RFM
- **R (Recency)**: kuintil 1–5; makin sedikit hari sejak order terakhir, makin tinggi skornya.
- **F (Frequency)**: 1× = 1, 2× = 2, 3× = 3, 4–5× = 4, ≥6× = 5.
  Ambang tetap dipakai karena 63% pelanggan di dataset hanya belanja sekali.
- **M (Monetary)**: kuintil 1–5; makin besar total belanja, makin tinggi skornya.

## Aturan segmen
| Segmen | Aturan | Jumlah (dataset bawaan) |
|---|---|---|
| Champions | R ≥ 4 dan rata-rata (F, M) ≥ 4 | 235 |
| Loyal | R ≥ 3 dan rata-rata (F, M) ≥ 3,5 | 157 |
| Potensial | R ≥ 3 (sisanya) | 928 |
| Berisiko | R ≤ 2 dan rata-rata (F, M) ≥ 3 | 200 |
| Tidak Aktif | R ≤ 2 dan rata-rata (F, M) < 3 | 674 |

Aturan bisa diubah di fungsi `segment_of()` pada `rfm.py`.

## Format data unggahan
Baris pertama berisi nama kolom. Kolom yang dibutuhkan:
`CustomerID`, `Recency` (hari), `Frequency` (jumlah pesanan), `Monetary` (total belanja, tanpa Rp).
Nama kolom lain juga bisa dipakai karena kolom dipetakan saat unggah.
