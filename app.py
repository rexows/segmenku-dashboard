"""SegmenKu — Dashboard Segmentasi Pelanggan (RFM) versi Streamlit.

Jalankan:  streamlit run app.py
"""
from __future__ import annotations

import io
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

import components as ui
import rfm

BASE = Path(__file__).parent
DATA_FILE = BASE / "data" / "RFM_data.csv"
BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]

st.set_page_config(page_title="SegmenKu", page_icon="◔", layout="wide", initial_sidebar_state="expanded")


# ---------------------------------------------------------------------------
# Gaya & data
# ---------------------------------------------------------------------------
@st.cache_data
def load_css() -> str:
    return (BASE / "assets" / "segmenku.css").read_text(encoding="utf-8") + "\n" + \
           (BASE / "assets" / "streamlit.css").read_text(encoding="utf-8")


@st.cache_data
def load_default() -> pd.DataFrame:
    return pd.read_csv(DATA_FILE)


@st.cache_data
def run_rfm(raw: pd.DataFrame) -> pd.DataFrame:
    return rfm.analyze(raw)


def today_label() -> str:
    d = date.today()
    return f"{d.day:02d} {BULAN[d.month - 1]} {d.year}"


def html(markup: str) -> None:
    st.html(markup)


def card_start() -> None:
    """Penanda agar container ini tampil sebagai kartu putih (lihat streamlit.css)."""
    st.html('<span class="card-marker"></span>')


st.markdown(f"<style>{load_css()}</style>", unsafe_allow_html=True)

if "dataset" not in st.session_state:
    st.session_state.dataset = {"name": DATA_FILE.name, "raw": load_default()}
    st.session_state.history = [{"name": DATA_FILE.name, "date": today_label(), "rows": len(load_default())}]
    st.session_state.seg_key = "champions"
    st.session_state.selected_id = None
    st.session_state.list_segment = "Semua Segmen"
    st.session_state.flash = None

DATA = run_rfm(st.session_state.dataset["raw"])
SOURCE = st.session_state.dataset["name"]


def by_segment(key: str) -> pd.DataFrame:
    return DATA[DATA["SegmentKey"] == key].sort_values("Monetary", ascending=False).reset_index(drop=True)


def styled_customers(df: pd.DataFrame):
    """Tabel interaktif dengan format Rupiah dan warna badge segmen."""
    view = df[["CustomerID", "Recency", "Frequency", "Monetary", "RFM", "Segmen"]].rename(columns={
        "CustomerID": "ID Pelanggan", "Recency": "Recency (hari)", "RFM": "Skor R-F-M"})

    def seg_style(v):
        s = rfm.SEG_BY_NAME.get(v)
        return f"background-color: {s['bg']}; color: {s['color']}; font-weight: 600" if s else ""

    styler = view.style.format({
        "Recency (hari)": lambda v: ui.fmt(v),
        "Frequency": lambda v: f"{ui.fmt(v)}×",
        "Monetary": ui.rupiah,
    })
    # Styler.map tersedia di pandas >= 2.1; applymap untuk versi lama
    styler = styler.map(seg_style, subset=["Segmen"]) if hasattr(styler, "map") else \
        styler.applymap(seg_style, subset=["Segmen"])
    return styler


# ---------------------------------------------------------------------------
# 01 — Dashboard
# ---------------------------------------------------------------------------
def page_dashboard():
    if st.session_state.flash:
        st.success(st.session_state.flash)
        st.session_state.flash = None

    head, action = st.columns([4, 1], vertical_alignment="center")
    with head:
        html(ui.page_header("Dashboard Segmentasi Pelanggan",
                            "Hasil segmentasi pelanggan dengan metode RFM (Recency, Frequency, Monetary)"))
    with action:
        if st.button("Unggah data baru", type="primary", use_container_width=True, key="dash-upload"):
            st.switch_page(PAGE_UPLOAD)

    total, sum_f, sum_m = len(DATA), DATA["Frequency"].sum(), DATA["Monetary"].sum()
    html(ui.metrics_row([
        ui.metric_card("Total Pelanggan", ui.fmt(total), f"Dari {SOURCE}", primary=True),
        ui.metric_card("Total Pesanan", ui.fmt(sum_f), f"Rata-rata {ui.dec(sum_f / total)} pesanan per pelanggan"),
        ui.metric_card("Total Penjualan", ui.rupiah_short(sum_m), f"Rata-rata {ui.rupiah_short(sum_m / total)} per pelanggan"),
        ui.metric_card("Jumlah Segmen", "5", "Berdasarkan analisis RFM"),
    ]))

    left, right = st.columns([650, 440], gap="medium")
    with left:
        with st.container():
            card_start()
            html(ui.card_title("Distribusi Segmen", "Proporsi pelanggan pada setiap segmen"))
            html(ui.donut_and_legend(DATA))
            choice = st.selectbox("Lihat detail segmen", [s["name"] for s in rfm.SEGMENTS],
                                  index=None, placeholder="Pilih segmen…", key="dash-seg")
            if choice:
                st.session_state.seg_key = rfm.SEG_BY_NAME[choice]["key"]
                st.session_state.selected_id = None
                st.session_state.pop("dash-seg", None)
                st.switch_page(PAGE_SEGMENT)

    with right:
        with st.container():
            card_start()
            html(ui.card_title("Unduh Hasil", "Ekspor hasil segmentasi untuk tim marketing"))
            base = Path(SOURCE).stem
            full_csv = rfm.export_table(DATA).to_csv(index=False).encode("utf-8-sig")
            summary_csv = rfm.summary_table(DATA).to_csv(index=False).encode("utf-8-sig")
            risk = rfm.export_table(DATA[DATA["SegmentKey"] == "berisiko"])
            risk_csv = risk.to_csv(index=False).encode("utf-8-sig")
            files = [
                ("csv", "Hasil Segmentasi Lengkap", f"CSV • {ui.fmt(total)} baris", f"{base}_hasil_segmentasi.csv", full_csv),
                ("xls", "Ringkasan per Segmen", "CSV • 5 baris", f"{base}_ringkasan_segmen.csv", summary_csv),
                ("pdf", "Daftar Win-back (Berisiko)", f"CSV • {ui.fmt(len(risk))} baris", f"{base}_winback_berisiko.csv", risk_csv),
            ]
            for kind, name, meta, fname, data in files:
                c1, c2 = st.columns([5, 1], vertical_alignment="center")
                with c1:
                    html(ui.file_item(kind, name, meta))
                with c2:
                    st.download_button("↓", data, file_name=fname, mime="text/csv",
                                       key=f"dl-{kind}", help=f"Unduh {fname}", use_container_width=True)

            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
                for _, _, _, fname, data in files:
                    z.writestr(fname, data)
            st.download_button("↓ Unduh Semua (.zip)", buf.getvalue(), file_name=f"{base}_segmentasi.zip",
                               mime="application/zip", type="primary", use_container_width=True, key="dl-all")

    with st.container():
        card_start()
        html(ui.card_title("Sebaran Recency", "Jumlah pelanggan berdasarkan jarak hari sejak pembelian terakhir"))
        html(ui.recency_histogram(DATA))

    with st.container():
        card_start()
        t1, t2 = st.columns([4, 1], vertical_alignment="center")
        with t1:
            html(ui.card_title("Pelanggan Teratas",
                               f"6 dari {ui.fmt(total)} pelanggan, diurutkan dari total belanja tertinggi"))
        with t2:
            if st.button("Lihat semua pelanggan →", use_container_width=True, key="dash-all"):
                st.switch_page(PAGE_CUSTOMERS)
        html(ui.customer_table(DATA.sort_values("Monetary", ascending=False).head(6)))


# ---------------------------------------------------------------------------
# 02 — Unggah Data
# ---------------------------------------------------------------------------
def page_upload():
    html(ui.page_header("Unggah Data", "Unggah data pelanggan untuk dianalisis dengan metode RFM"))

    upload = st.session_state.get("uploader")
    html(ui.steps(2 if upload else 1))

    left, right = st.columns([710, 380], gap="medium")
    with left:
        with st.container():
            card_start()
            file = st.file_uploader("Seret file ke sini atau klik untuk memilih",
                                    type=["csv", "xlsx"], key="uploader",
                                    help="Format CSV atau Excel (.xlsx), maksimal 10 MB")

            raw = None
            if file is not None:
                try:
                    raw = rfm.read_upload(file)
                except Exception as exc:  # noqa: BLE001 — tampilkan pesan yang jelas ke pengguna
                    st.error(f"File tidak bisa dibaca: {exc}. Pastikan file berformat CSV atau Excel yang valid.")

            html(ui.card_title("Petakan kolom", "Pilih kolom di file Anda untuk setiap data yang dibutuhkan"))
            cols = list(raw.columns) if raw is not None else []
            fields = [
                ("id", "ID pelanggan"),
                ("recency", "Recency (hari sejak order terakhir)"),
                ("frequency", "Frequency (jumlah pesanan)"),
                ("monetary", "Monetary (total belanja)"),
            ]
            picked = {}
            grid = st.columns(2)
            for i, (field, label) in enumerate(fields):
                with grid[i % 2]:
                    picked[field] = st.selectbox(
                        label, cols, index=rfm.guess_column(cols, field) if cols else None,
                        placeholder="Pilih kolom…", disabled=raw is None,
                        key=f"map-{field}-{file.name if file is not None else 'kosong'}")

            html(ui.card_title("Pratinjau data"))
            if raw is None:
                st.caption("Pilih file untuk melihat pratinjau dan memulai analisis.")
            else:
                st.caption(f"{ui.fmt(len(raw))} baris • {len(cols)} kolom")
                st.dataframe(raw.head(5), use_container_width=True, hide_index=True)

            chosen = [picked[f] for f, _ in fields]
            ready = raw is not None and all(chosen) and len(set(chosen)) == 4
            if raw is not None and not ready:
                st.warning("Pilih kolom yang berbeda untuk keempat isian sebelum memulai analisis.")

            if st.button("Mulai analisis", type="primary", disabled=not ready, key="analyze"):
                clean, skipped = rfm.clean_upload(raw, *chosen)
                if len(clean) < 5:
                    st.error(f"Hanya {len(clean)} baris yang valid. Periksa apakah kolom sudah dipetakan "
                             "dengan benar dan berisi angka.")
                else:
                    st.session_state.dataset = {"name": file.name, "raw": clean}
                    st.session_state.history.insert(0, {"name": file.name, "date": today_label(), "rows": len(clean)})
                    st.session_state.selected_id = None
                    st.session_state.flash = (
                        f"Analisis selesai: {ui.fmt(len(clean))} pelanggan dari {file.name} disegmentasi"
                        + (f", {ui.fmt(skipped)} baris dilewati karena datanya tidak lengkap." if skipped else ".")
                    )
                    st.switch_page(PAGE_DASHBOARD)

    with right:
        with st.container():
            card_start()
            html(ui.one_line("""
              <h2 class="card__title">Format file</h2>
              <p class="info-text" style="margin-top:16px">Baris pertama berisi nama kolom.<br>Kolom yang dibutuhkan:</p>
              <div class="chips">
                <span class="chip">CustomerID</span><span class="chip">Recency</span>
                <span class="chip">Frequency</span><span class="chip">Monetary</span>
              </div>
              <p class="info-text info-text--sm" style="margin-top:20px">Recency ditulis dalam hari (contoh: 48).<br>Monetary berupa angka tanpa Rp.</p>
              <h2 class="card__title" style="margin-top:32px">Riwayat unggahan</h2>"""))
            html(ui.history_list(st.session_state.history))


# ---------------------------------------------------------------------------
# 03 — Pelanggan
# ---------------------------------------------------------------------------
SORTS = {
    "Total belanja tertinggi": (["Monetary"], [False]),
    "Frekuensi tertinggi": (["Frequency", "Monetary"], [False, False]),
    "Order paling baru": (["Recency", "Monetary"], [True, False]),
    "Order paling lama": (["Recency"], [False]),
    "ID pelanggan (A–Z)": (["CustomerID"], [True]),
}


def page_customers():
    head, action = st.columns([4, 1], vertical_alignment="center")
    with head:
        html(ui.page_header("Pelanggan", "Telusuri pelanggan beserta segmennya. Pilih baris untuk melihat detail."))
    with action:
        if st.button("Unggah data baru", type="primary", use_container_width=True, key="cust-upload"):
            st.switch_page(PAGE_UPLOAD)

    with st.container():
        card_start()
        counts = DATA["Segmen"].value_counts()
        seg_options = ["Semua Segmen"] + [s["name"] for s in rfm.SEGMENTS]
        f1, f2, f3 = st.columns([460, 190, 370])
        with f1:
            q = st.text_input("Cari", placeholder="⌕   Cari ID pelanggan…", label_visibility="collapsed", key="f-search")
        with f2:
            seg = st.selectbox("Segmen", seg_options, label_visibility="collapsed", key="list_segment",
                               format_func=lambda s: f"{s} ({ui.fmt(len(DATA) if s == 'Semua Segmen' else counts.get(s, 0))})")
        with f3:
            sort = st.selectbox("Urutkan", list(SORTS), label_visibility="collapsed", key="f-sort")

        view = DATA
        if seg != "Semua Segmen":
            view = view[view["Segmen"] == seg]
        if q.strip():
            view = view[view["CustomerID"].astype(str).str.lower().str.contains(q.strip().lower(), regex=False)]
        by, asc = SORTS[sort]
        view = view.sort_values(by, ascending=asc).reset_index(drop=True)

        if view.empty:
            st.info("Tidak ada pelanggan yang cocok dengan filter ini.")
            return

        event = st.dataframe(styled_customers(view), use_container_width=True, hide_index=True, height=560,
                             on_select="rerun", selection_mode="single-row", key="cust-table")
        st.caption(f"Menampilkan {ui.fmt(len(view))} dari {ui.fmt(len(DATA))} pelanggan • klik baris untuk membuka detail")

        rows = event.selection.rows if event else []
        if rows:
            picked = view.iloc[rows[0]]
            st.session_state.seg_key = picked["SegmentKey"]
            st.session_state.selected_id = picked["CustomerID"]
            st.session_state.pop("cust-table", None)
            st.session_state.pop(f"seg-table-{picked['SegmentKey']}", None)
            st.switch_page(PAGE_SEGMENT)


# ---------------------------------------------------------------------------
# 04 — Detail Segmen
# ---------------------------------------------------------------------------
def page_segment():
    names = [s["name"] for s in rfm.SEGMENTS]
    current = rfm.SEG_BY_KEY[st.session_state.seg_key]

    head, action = st.columns([4, 1], vertical_alignment="center")
    with head:
        html(ui.page_header(f"Segmen {current['name']}", current["desc"]))
    with action:
        if st.button("Lihat di halaman Pelanggan", type="primary", use_container_width=True, key="seg-list"):
            st.session_state.list_segment = current["name"]
            st.switch_page(PAGE_CUSTOMERS)

    picked = st.segmented_control("Pilih segmen", names, default=current["name"],
                                  label_visibility="collapsed", key=f"seg-tabs-{current['key']}")
    if picked and picked != current["name"]:
        st.session_state.seg_key = rfm.SEG_BY_NAME[picked]["key"]
        st.session_state.selected_id = None
        st.rerun()

    members = by_segment(current["key"])
    total = len(DATA)
    share = members["Monetary"].sum() / DATA["Monetary"].sum() * 100 if DATA["Monetary"].sum() else 0
    has = len(members) > 0
    html(ui.metrics_row([
        ui.metric_card("Jumlah pelanggan", ui.fmt(len(members)), f"{ui.dec(len(members) / total * 100)}% dari total pelanggan", primary=True),
        ui.metric_card("Rata-rata recency", f"{ui.fmt(members['Recency'].mean()) if has else 0} hari", "Sejak order terakhir"),
        ui.metric_card("Rata-rata pesanan", ui.dec(members["Frequency"].mean()) if has else "0", "Pesanan per pelanggan"),
        ui.metric_card("Rata-rata belanja", ui.rupiah_short(members["Monetary"].mean()) if has else "Rp 0",
                       f"{ui.dec(share)}% dari total penjualan"),
    ]))

    html(f'<div class="card"><h2 class="card__title">Saran tindakan</h2><p class="advice">{current["advice"]}</p></div>')

    left, right = st.columns([2.2, 1], gap="medium")
    with left:
        with st.container():
            card_start()
            html(ui.card_title("Pelanggan di segmen ini",
                               f"Diurutkan dari total belanja tertinggi. Aturan segmen: {current['rule']}."))
            if not has:
                st.info("Belum ada pelanggan di segmen ini.")
            else:
                event = st.dataframe(styled_customers(members), use_container_width=True, hide_index=True,
                                     height=460, on_select="rerun", selection_mode="single-row",
                                     key=f"seg-table-{current['key']}")
                rows = event.selection.rows if event else []
                if rows:
                    st.session_state.selected_id = members.iloc[rows[0]]["CustomerID"]
                st.caption(f"{ui.fmt(len(members))} pelanggan • klik baris untuk melihat detail")

    with right:
        if has:
            sel = members[members["CustomerID"] == st.session_state.selected_id]
            row = sel.iloc[0] if not sel.empty else members.iloc[0]
            html(ui.detail_card(row))


# ---------------------------------------------------------------------------
# Navigasi
# ---------------------------------------------------------------------------
PAGE_DASHBOARD = st.Page(page_dashboard, title="Dashboard", icon=":material/dashboard:", url_path="dashboard", default=True)
PAGE_UPLOAD = st.Page(page_upload, title="Unggah Data", icon=":material/upload:", url_path="unggah")
PAGE_CUSTOMERS = st.Page(page_customers, title="Pelanggan", icon=":material/group:", url_path="pelanggan")
PAGE_SEGMENT = st.Page(page_segment, title="Detail Segmen", icon=":material/donut_large:", url_path="segmen")

st.logo(str(BASE / "assets" / "logo.svg"))
nav = st.navigation([PAGE_DASHBOARD, PAGE_UPLOAD, PAGE_CUSTOMERS, PAGE_SEGMENT])
with st.sidebar:
    st.html(ui.sidebar_info(SOURCE, len(DATA)))
nav.run()
