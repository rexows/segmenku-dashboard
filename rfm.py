"""Logika RFM untuk SegmenKu.

Skor:
- R (Recency): kuintil 1–5 dari peringkat persentil; makin sedikit hari, makin tinggi.
- F (Frequency): ambang tetap 1×=1, 2×=2, 3×=3, 4–5×=4, ≥6×=5.
  Dipakai ambang tetap karena mayoritas pelanggan hanya belanja sekali,
  sehingga kuintil biasa tidak bisa membedakan mereka.
- M (Monetary): kuintil 1–5 dari peringkat persentil; makin besar, makin tinggi.
"""
from __future__ import annotations

import math
import re

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Definisi segmen (warna diambil dari assets/segmenku.css)
# ---------------------------------------------------------------------------
SEGMENTS = [
    {
        "key": "champions", "name": "Champions",
        "color": "#4f46e5", "bg": "rgba(79, 70, 229, 0.13)",
        "desc": "Pelanggan terbaik: baru saja belanja, sering belanja, dan nilai belanjanya tinggi.",
        "rule": "Skor R ≥ 4 dan rata-rata skor F & M ≥ 4",
        "advice": "Beri akses awal produk baru dan program loyalitas eksklusif. "
                  "Ajak mereka memberi ulasan atau ikut program referral.",
    },
    {
        "key": "loyal", "name": "Loyal",
        "color": "#0ea5e9", "bg": "rgba(14, 165, 233, 0.13)",
        "desc": "Masih aktif dan belanja cukup sering dengan nilai yang baik.",
        "rule": "Skor R ≥ 3 dan rata-rata skor F & M ≥ 3,5",
        "advice": "Tawarkan upsell, bundling, dan poin loyalitas supaya mereka naik ke segmen Champions.",
    },
    {
        "key": "potensial", "name": "Potensial",
        "color": "#10b981", "bg": "rgba(16, 185, 129, 0.13)",
        "desc": "Masih aktif belanja, tetapi frekuensi atau nilai belanjanya masih rendah.",
        "rule": "Skor R ≥ 3, belum memenuhi syarat Loyal",
        "advice": "Kirim rekomendasi produk yang relevan dan promo untuk pembelian berikutnya "
                  "agar mereka terbiasa belanja ulang.",
    },
    {
        "key": "berisiko", "name": "Berisiko",
        "color": "#f59e0b", "bg": "rgba(245, 158, 11, 0.13)",
        "desc": "Dulu bernilai cukup tinggi, tetapi sudah lama tidak belanja.",
        "rule": "Skor R ≤ 2 dan rata-rata skor F & M ≥ 3",
        "advice": "Hubungi dengan penawaran win-back yang personal, misalnya voucher khusus atau "
                  "pengingat produk favorit, sebelum mereka berhenti.",
    },
    {
        "key": "tidak-aktif", "name": "Tidak Aktif",
        "color": "#ef4444", "bg": "rgba(239, 68, 68, 0.13)",
        "desc": "Sudah lama tidak belanja dan nilai belanjanya rendah.",
        "rule": "Skor R ≤ 2 dan rata-rata skor F & M < 3",
        "advice": "Kirim kampanye reaktivasi berbiaya rendah (email massal, promo umum). "
                  "Jika tetap tidak merespons, kurangi frekuensi kontak.",
    },
]
SEG_BY_KEY = {s["key"]: s for s in SEGMENTS}
SEG_BY_NAME = {s["name"]: s for s in SEGMENTS}


# ---------------------------------------------------------------------------
# Skoring
# ---------------------------------------------------------------------------
def quintile_scores(values: pd.Series, higher_is_better: bool) -> pd.Series:
    """Peringkat persentil (rata-rata untuk nilai kembar) lalu dibagi ke 5 kelompok."""
    n = len(values)
    pct = values.rank(method="average", pct=True)
    q = pct if higher_is_better else 1 - pct + 1 / n
    return np.clip(np.ceil(q * 5), 1, 5).astype(int)


def freq_score(f: int) -> int:
    if f >= 6:
        return 5
    if f >= 4:
        return 4
    if f == 3:
        return 3
    if f == 2:
        return 2
    return 1


def segment_of(r: int, f: int, m: int) -> str:
    fm = (f + m) / 2
    if r >= 4 and fm >= 4:
        return "champions"
    if r >= 3 and fm >= 3.5:
        return "loyal"
    if r >= 3:
        return "potensial"
    if fm >= 3:
        return "berisiko"
    return "tidak-aktif"


def analyze(raw: pd.DataFrame) -> pd.DataFrame:
    """raw harus punya kolom: CustomerID, Recency, Frequency, Monetary."""
    df = raw.copy().reset_index(drop=True)
    df["R"] = quintile_scores(df["Recency"], higher_is_better=False)
    df["F"] = df["Frequency"].astype(int).map(freq_score)
    df["M"] = quintile_scores(df["Monetary"], higher_is_better=True)
    df["RFM"] = df["R"].astype(str) + "-" + df["F"].astype(str) + "-" + df["M"].astype(str)
    df["SegmentKey"] = [segment_of(r, f, m) for r, f, m in zip(df["R"], df["F"], df["M"])]
    df["Segmen"] = df["SegmentKey"].map(lambda k: SEG_BY_KEY[k]["name"])
    return df


# ---------------------------------------------------------------------------
# Membaca & membersihkan file unggahan
# ---------------------------------------------------------------------------
def to_number(v) -> float:
    if pd.isna(v):
        return math.nan
    if isinstance(v, (int, float, np.integer, np.floating)):
        return float(v)
    s = re.sub(r"(?i)rp", "", str(v)).replace(" ", "").strip()
    if re.fullmatch(r"-?\d{1,3}(\.\d{3})+(,\d+)?", s):      # 1.250.000,50
        s = s.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"-?\d+,\d+", s):                      # 1250,5
        s = s.replace(",", ".")
    else:                                                    # 1,250,000.50
        s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return math.nan


def read_upload(file) -> pd.DataFrame:
    name = file.name.lower()
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(file, dtype=str)
    return pd.read_csv(file, sep=None, engine="python", dtype=str, encoding="utf-8-sig")


GUESS_PATTERNS = {
    "id": ["customerid", "idpelanggan", "customer", "pelanggan", "id"],
    "recency": ["recency", "hari", "days"],
    "frequency": ["frequency", "frekuensi", "jumlahpesanan", "pesanan", "orders"],
    "monetary": ["monetary", "totalbelanja", "belanja", "total", "amount", "sales"],
}


def guess_column(columns: list[str], field: str) -> int | None:
    low = [re.sub(r"[^a-z]", "", str(c).lower()) for c in columns]
    for p in GUESS_PATTERNS[field]:
        for i, c in enumerate(low):
            if p in c:
                return i
    return None


def clean_upload(df: pd.DataFrame, col_id: str, col_r: str, col_f: str, col_m: str) -> tuple[pd.DataFrame, int]:
    out = pd.DataFrame({
        "CustomerID": df[col_id].astype(str).str.strip(),
        "Recency": df[col_r].map(to_number),
        "Frequency": df[col_f].map(to_number),
        "Monetary": df[col_m].map(to_number),
    })
    valid = (
        out["CustomerID"].ne("") & out["CustomerID"].ne("nan")
        & out[["Recency", "Frequency", "Monetary"]].notna().all(axis=1)
        & (out["Recency"] >= 0) & (out["Frequency"] >= 1) & (out["Monetary"] >= 0)
    )
    skipped = int((~valid).sum())
    out = out[valid].copy()
    out["Frequency"] = out["Frequency"].round().astype(int)
    return out.reset_index(drop=True), skipped


# ---------------------------------------------------------------------------
# Ringkasan & ekspor
# ---------------------------------------------------------------------------
def summary_table(df: pd.DataFrame) -> pd.DataFrame:
    total = len(df)
    rows = []
    for s in SEGMENTS:
        part = df[df["SegmentKey"] == s["key"]]
        rows.append({
            "Segmen": s["name"],
            "Jumlah_Pelanggan": len(part),
            "Persen": round(len(part) / total * 100, 1) if total else 0,
            "Rata_Recency_Hari": round(part["Recency"].mean(), 1) if len(part) else 0,
            "Rata_Frequency": round(part["Frequency"].mean(), 2) if len(part) else 0,
            "Rata_Monetary": round(part["Monetary"].mean()) if len(part) else 0,
            "Total_Monetary": round(part["Monetary"].sum()),
            "Saran_Tindakan": s["advice"],
        })
    return pd.DataFrame(rows)


def export_table(df: pd.DataFrame) -> pd.DataFrame:
    out = df.sort_values("Monetary", ascending=False)
    return out[["CustomerID", "Recency", "Frequency", "Monetary", "R", "F", "M", "RFM", "Segmen"]].rename(
        columns={"R": "R_Score", "F": "F_Score", "M": "M_Score", "RFM": "RFM_Score"})
