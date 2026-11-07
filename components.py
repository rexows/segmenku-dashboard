"""Potongan HTML yang memakai class dari assets/segmenku.css."""
from __future__ import annotations

import math
from html import escape

import pandas as pd

from rfm import SEG_BY_KEY, SEGMENTS


# ---------------------------------------------------------------------------
# Format angka gaya Indonesia
# ---------------------------------------------------------------------------
def fmt(n: float) -> str:
    return f"{n:,.0f}".replace(",", ".")


def dec(n: float, d: int = 1) -> str:
    return f"{n:,.{d}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def rupiah(n: float) -> str:
    return "Rp " + fmt(n)


def rupiah_short(n: float) -> str:
    if n >= 1e9:
        return f"Rp {dec(n / 1e9, 2)} M"
    if n >= 1e6:
        return f"Rp {dec(n / 1e6, 1)} jt"
    if n >= 1e3:
        return f"Rp {dec(n / 1e3, 0)} rb"
    return rupiah(n)


def one_line(html: str) -> str:
    """Rapatkan HTML supaya tidak dianggap blok kode oleh Markdown."""
    return "".join(line.strip() for line in html.splitlines())


# ---------------------------------------------------------------------------
# Komponen
# ---------------------------------------------------------------------------
def page_header(title: str, subtitle: str) -> str:
    return one_line(f"""
      <div class="page-header-text">
        <h1 class="page-title">{escape(title)}</h1>
        <p class="page-subtitle">{escape(subtitle)}</p>
      </div>""")


def metric_card(label: str, value: str, note: str, primary: bool = False) -> str:
    return one_line(f"""
      <div class="metric{' metric--primary' if primary else ''}">
        <div class="metric__label">{escape(label)}</div>
        <div class="metric__value">{escape(value)}</div>
        <div class="metric__trend">{escape(note)}</div>
      </div>""")


def metrics_row(cards: list[str]) -> str:
    return f'<div class="metrics">{"".join(cards)}</div>'


def badge(key: str) -> str:
    return f'<span class="badge badge--{key}">{SEG_BY_KEY[key]["name"]}</span>'


def card_title(title: str, subtitle: str = "") -> str:
    sub = f'<p class="card__subtitle">{escape(subtitle)}</p>' if subtitle else ""
    return f'<div class="card-head"><h2 class="card__title">{escape(title)}</h2>{sub}</div>'


def donut_and_legend(df: pd.DataFrame) -> str:
    total = len(df)
    counts = {s["key"]: int((df["SegmentKey"] == s["key"]).sum()) for s in SEGMENTS}
    r, gap = 62, 2.5
    circ = 2 * math.pi * r
    offset, arcs = 0.0, ""
    for s in SEGMENTS:
        n = counts[s["key"]]
        if not n:
            continue
        length = n / total * circ
        draw = max(length - gap, 0.5)
        arcs += (
            f'<circle cx="80" cy="80" r="{r}" fill="none" stroke="{s["color"]}" stroke-width="26" '
            f'stroke-dasharray="{draw:.2f} {circ - draw:.2f}" stroke-dashoffset="{-offset:.2f}" '
            f'transform="rotate(-90 80 80)"><title>{s["name"]}: {fmt(n)} pelanggan '
            f'({dec(n / total * 100)}%)</title></circle>'
        )
        offset += length

    mx = max(counts.values()) or 1
    legend = ""
    for s in SEGMENTS:
        n = counts[s["key"]]
        legend += one_line(f"""
          <div class="legend-row">
            <span class="legend-dot" style="background:{s['color']}"></span>
            <span class="legend-row__name">{s['name']}</span>
            <span class="progress"><span class="progress__fill" style="display:block;width:{n / mx * 100:.1f}%;background:{s['color']}"></span></span>
            <span class="legend-row__value">{fmt(n)}</span>
            <span class="legend-row__pct">{round(n / total * 100) if total else 0}%</span>
          </div>""")

    return one_line(f"""
      <div class="dist">
        <div class="donut">
          <svg viewBox="0 0 160 160" role="img" aria-label="Diagram donat distribusi segmen">
            <circle cx="80" cy="80" r="{r}" fill="none" stroke="#eef0ff" stroke-width="26"></circle>{arcs}
          </svg>
          <div class="donut__center">
            <div class="donut__value">{fmt(total)}</div>
            <div class="donut__label">Total Pelanggan</div>
          </div>
        </div>
        <div class="legend">{legend}</div>
      </div>""")


def _nice_step(raw: float) -> float:
    p = 10 ** math.floor(math.log10(max(raw, 1)))
    f = raw / p
    return (1 if f <= 1 else 2 if f <= 2 else 5 if f <= 5 else 10) * p


def recency_histogram(df: pd.DataFrame) -> str:
    buckets = [
        ("0–30 hari", lambda d: d <= 30),
        ("31–90 hari", lambda d: (d > 30) & (d <= 90)),
        ("91–180 hari", lambda d: (d > 90) & (d <= 180)),
        ("181–365 hari", lambda d: (d > 180) & (d <= 365)),
        ("> 365 hari", lambda d: d > 365),
    ]
    counts = [int(test(df["Recency"]).sum()) for _, test in buckets]
    total = len(df) or 1
    W, H, pad_l, pad_r, pad_t, pad_b = 1000, 220, 44, 10, 24, 30
    step = _nice_step(max(max(counts), 1) / 4)
    top = math.ceil(max(max(counts), 1) / step) * step

    def y(v):
        return pad_t + (H - pad_t - pad_b) * (1 - v / top)

    bw = (W - pad_l - pad_r) / len(buckets)
    svg = ""
    v = 0
    while v <= top:
        svg += (f'<line x1="{pad_l}" x2="{W - pad_r}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="#e5e7f5" stroke-width="1"></line>'
                f'<text x="{pad_l - 8}" y="{y(v) + 3:.1f}" text-anchor="end" fill="#626783" font-size="10">{fmt(v)}</text>')
        v += step
    for i, ((label, _), n) in enumerate(zip(buckets, counts)):
        x = pad_l + i * bw + bw * 0.22
        w = bw * 0.56
        yy = y(n)
        h = max(y(0) - yy, 0)
        rr = min(4, h)
        path = (f"M{x:.1f},{y(0):.1f} V{yy + rr:.1f} Q{x:.1f},{yy:.1f} {x + rr:.1f},{yy:.1f} "
                f"H{x + w - rr:.1f} Q{x + w:.1f},{yy:.1f} {x + w:.1f},{yy + rr:.1f} V{y(0):.1f} Z") if h > 0 else ""
        svg += (f'<path d="{path}" fill="#4f46e5"><title>{label}: {fmt(n)} pelanggan ({dec(n / total * 100)}%)</title></path>'
                f'<text x="{x + w / 2:.1f}" y="{yy - 7:.1f}" text-anchor="middle" fill="#171735" font-size="11" font-weight="700">{fmt(n)}</text>'
                f'<text x="{x + w / 2:.1f}" y="{H - 10}" text-anchor="middle" fill="#626783" font-size="10">{label}</text>')
    return f'<svg class="histo" viewBox="0 0 {W} {H}" role="img" aria-label="Grafik batang sebaran recency">{svg}</svg>'


def customer_table(df: pd.DataFrame) -> str:
    head = one_line("""
      <thead><tr>
        <th>ID Pelanggan</th><th class="r">Recency</th><th class="r">Frequency</th>
        <th class="r">Monetary</th><th class="c">Skor R-F-M</th><th>Segmen</th>
      </tr></thead>""")
    body = "".join(one_line(f"""
      <tr>
        <td class="table__id">{escape(str(row.CustomerID))}</td>
        <td class="r">{fmt(row.Recency)} hari</td>
        <td class="r">{fmt(row.Frequency)}×</td>
        <td class="r">{rupiah(row.Monetary)}</td>
        <td class="c"><span class="score">{row.RFM}</span></td>
        <td>{badge(row.SegmentKey)}</td>
      </tr>""") for row in df.itertuples())
    return f'<div class="table-wrap"><table class="table">{head}<tbody>{body}</tbody></table></div>'


def file_item(kind: str, name: str, meta: str) -> str:
    return one_line(f"""
      <div class="file-item">
        <span class="file-item__type file-item__type--{kind}">CSV</span>
        <span class="file-item__text">
          <span class="file-item__name" style="display:block">{escape(name)}</span>
          <span class="file-item__meta" style="display:block">{escape(meta)}</span>
        </span>
      </div>""")


def steps(active: int) -> str:
    labels = ["Pilih file", "Petakan kolom", "Analisis RFM"]
    parts = []
    for i, label in enumerate(labels, start=1):
        cls = "step is-active" if i <= active else "step"
        parts.append(f'<div class="{cls}"><span class="step__number">{i}</span>{label}</div>')
    return '<div class="steps">' + '<span class="step__line"></span>'.join(parts) + "</div>"


def history_list(items: list[dict]) -> str:
    rows = "".join(one_line(f"""
      <div class="history__item">
        <div>
          <div class="history__name">{escape(h['name'])}</div>
          <div class="history__meta">{escape(h['date'])} • {fmt(h['rows'])} baris</div>
        </div>
        <span class="status-done">{'Aktif' if i == 0 else 'Selesai'}</span>
      </div>""") for i, h in enumerate(items))
    return f'<div class="history">{rows}</div>'


def detail_card(row) -> str:
    seg = SEG_BY_KEY[row["SegmentKey"]]
    initials = str(row["CustomerID"]).replace(" ", "")[-2:].upper()

    def bar(label, v):
        return one_line(f"""
          <div class="detail-bar">
            <span class="detail-bar__label">{label}</span>
            <span class="progress progress--lg"><span class="progress__fill" style="display:block;width:{v * 20}%;background:{seg['color']}"></span></span>
            <span class="detail-bar__val">{v}</span>
          </div>""")

    return one_line(f"""
      <div class="card card--outlined">
        <h2 class="card__title">Detail pelanggan</h2>
        <div class="detail-head">
          <span class="avatar avatar--lg" style="background:{seg['color']}">{escape(initials)}</span>
          <div>
            <div class="detail-name">{escape(str(row['CustomerID']))}</div>
            <div class="detail-sub">Skor R-F-M {row['RFM']}</div>
          </div>
        </div>
        <div style="margin-top:12px">{badge(row['SegmentKey'])}</div>
        <div class="detail-bars">{bar('Recency', int(row['R']))}{bar('Frequency', int(row['F']))}{bar('Monetary', int(row['M']))}</div>
        <div class="detail-facts">
          <div class="detail-fact"><span>Total belanja</span><span>{rupiah(row['Monetary'])}</span></div>
          <div class="detail-fact"><span>Jumlah pesanan</span><span>{fmt(row['Frequency'])}×</span></div>
          <div class="detail-fact"><span>Order terakhir</span><span>{fmt(row['Recency'])} hari lalu</span></div>
        </div>
      </div>""")


def sidebar_info(source: str, n: int) -> str:
    return one_line(f"""
      <div class="sidebar__info">
        <div class="sidebar__info-title">Analisis RFM aktif</div>
        <div class="sidebar__info-text">{escape(source)} • {fmt(n)} pelanggan</div>
      </div>""")
