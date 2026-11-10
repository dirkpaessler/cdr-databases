#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""EU27 carbon removal companies: one map per pathway, and the 27 member states as bars.

Reads two files of a data release in this repository (companies.csv and
researchers_by_country.csv under v1/<release>/) and the country outlines in
examples/world-110m.json (Natural Earth 110m as TopoJSON, from the world-atlas
project). No GIS library: the TopoJSON is decoded by hand and projected with a
Lambert azimuthal equal-area projection centred on 10° E, 52° N, the choice of
the EU's EPSG:3035 grid. Needs Python 3.9 or newer and matplotlib.

Run:
    python3 examples/eu27_company_maps.py                      # release 2026-11.4, as in the article
    python3 examples/eu27_company_maps.py --release latest --out charts/

Outputs (into --out, default the current directory):
    eu27-companies-one-map-per-pathway.png   seven EU maps on one colour scale
    eu27-companies-by-member-state.png       all 27 member states as stacked bars
    eu27-companies-by-member-state.csv       the table behind both

Article: https://captaindrawdown.com/posts/eu27-carbon-removal-companies-one-map-per-pathway/
The published charts are set in Inter and carry the Carbon Drawdown Initiative
logo; this script falls back to a system font and draws no logo.

Licence: MIT for this script (examples/LICENSE). The data keeps its own
licences, see the main README.
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.patches import Patch, Polygon as MplPolygon  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
TOPO = HERE / "world-110m.json"

EU27 = frozenset({
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR",
    "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK",
    "SI", "ES", "SE",
})
NAMES = {
    "AT": "Austria", "BE": "Belgium", "BG": "Bulgaria", "CY": "Cyprus", "CZ": "Czechia",
    "DE": "Germany", "DK": "Denmark", "EE": "Estonia", "ES": "Spain", "FI": "Finland",
    "FR": "France", "GR": "Greece", "HR": "Croatia", "HU": "Hungary", "IE": "Ireland",
    "IT": "Italy", "LT": "Lithuania", "LU": "Luxembourg", "LV": "Latvia", "MT": "Malta",
    "NL": "Netherlands", "PL": "Poland", "PT": "Portugal", "RO": "Romania", "SE": "Sweden",
    "SI": "Slovenia", "SK": "Slovakia",
}
TOPO_NAMES = {v: k for k, v in NAMES.items()}   # Natural Earth spells them the same way
MALTA = (14.4, 35.9)                             # not in the 110m file: drawn as a dot

# pathway_primary values of companies.csv
NARROW = ("BECCS", "DAC")
OTHER = ("Biochar", "Enhanced Weathering", "Mineralization", "Ocean CDR", "Biomass Burial")
PERMANENT = NARROW + OTHER                      # every pathway with a removal
ENABLING = "Enabling Tech"                      # not a removal pathway, not on the maps
PATHWAY_PANELS = [
    ("BECCS", "BioCCS"), ("DAC", "DACCS"), ("Biochar", "Biochar"),
    ("Enhanced Weathering", "Enhanced weathering"), ("Mineralization", "Mineralisation"),
    ("Ocean CDR", "Ocean CDR"), ("Biomass Burial", "Biomass burial"),
]

INK = "#15262c"
INK_MUTED = "#56666b"
LINE = "#d9dfde"
PETROL = "#0e5a6a"
SURFACE = "#ffffff"
# One petrol ramp, light to dark (sequential = one hue), plus two greys.
RAMP = ["#cfe3e7", "#8fbfc8", "#4b94a2", PETROL, "#083a45"]
ZERO = "#e4e8e9"          # EU member state without a published company
OUTSIDE = "#f4f5f5"       # not an EU member state
COMPANY_BINS = [(1, 2, "1 to 2"), (3, 9, "3 to 9"), (10, 29, "10 to 29"), (30, 10 ** 6, "30 or more")]


# ── data ──────────────────────────────────────────────────────────────

def load_companies(data: Path) -> dict[str, collections.Counter]:
    """Member state -> companies per primary pathway."""
    tab = {cc: collections.Counter() for cc in EU27}
    with open(data / "companies.csv", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["country_code"] in tab:
                tab[r["country_code"]][r["pathway_primary"]] += 1
    return tab


def load_researchers(data: Path) -> dict[str, int]:
    by_cc = {}
    with open(data / "researchers_by_country.csv", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["country_code"] in EU27:
                by_cc[r["country_code"]] = int(r["researchers"])
    return by_cc


def narrow(t) -> int:
    return sum(t[p] for p in NARROW)


def permanent(t) -> int:
    return sum(t[p] for p in PERMANENT)


def n_states(values: dict[str, int]) -> int:
    return sum(1 for x in values.values() if x > 0)


# ── map ───────────────────────────────────────────────────────────────

LON0, LAT0 = math.radians(10.0), math.radians(52.0)   # Lambert azimuthal equal-area, Europe (as EPSG:3035)


def project(lon: float, lat: float):
    lon = math.radians(max(-40.0, min(75.0, lon)))
    lat = math.radians(max(15.0, min(85.0, lat)))
    c = 1 + math.sin(LAT0) * math.sin(lat) + math.cos(LAT0) * math.cos(lat) * math.cos(lon - LON0)
    if c <= 1e-9:
        return None
    k = math.sqrt(2 / c)
    return (k * math.cos(lat) * math.sin(lon - LON0),
            k * (math.cos(LAT0) * math.sin(lat) - math.sin(LAT0) * math.cos(lat) * math.cos(lon - LON0)))


def load_shapes() -> dict[str, list[list[tuple[float, float]]]]:
    """Country name -> list of projected exterior rings (holes dropped)."""
    topo = json.loads(TOPO.read_text(encoding="utf-8"))
    sc, tr = topo["transform"]["scale"], topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:          # delta-encoded integer coordinates
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * sc[0] + tr[0], y * sc[1] + tr[1]))
        arcs.append(pts)

    def ring(ids):
        pts = []
        for i in ids:                 # a negative index is the arc reversed
            a = arcs[i] if i >= 0 else arcs[~i][::-1]
            pts.extend(a if not pts else a[1:])
        return [p for p in (project(*q) for q in pts) if p]

    shapes = {}
    for g in topo["objects"]["countries"]["geometries"]:
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
        shapes[g["properties"]["name"]] = [ring(p[0]) for p in polys]
    return shapes


def area_centroid(ring):
    a = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]):
        f = x0 * y1 - x1 * y0
        a += f
        cx += (x0 + x1) * f
        cy += (y0 + y1) * f
    if abs(a) < 1e-12:
        return 0.0, ring[0]
    return abs(a) / 2, (cx / (3 * a), cy / (3 * a))


def bin_colour(value: int) -> str:
    if value <= 0:
        return ZERO
    for i, (lo, hi, _label) in enumerate(COMPANY_BINS):
        if lo <= value <= hi:
            return RAMP[i + 1]
    return RAMP[-1]


# Label nudges in projected units for states whose centroid is awkward.
NUDGE = {"GR": (-0.006, 0.0), "SE": (0.0, -0.02), "FI": (0.0, -0.01), "IT": (-0.02, 0.04), "FR": (0.0, 0.01)}
# A number sits on a country only where it has room: the larger states by
# projected area (equal-area projection, unit sphere) plus Ireland. The small
# ones (Benelux, Denmark, the Baltics, Slovenia, Croatia, Slovakia, Cyprus,
# Malta) are read from the bar chart.
LABEL_MIN_AREA = 0.0019
LABEL_ALWAYS = {"IE"}
# Map window: longitude -10.5 to 35, latitude 34.5 to 71.5 (Portugal to Cyprus,
# Malta to the North Cape); the frame is the projected image of that box.
WINDOW = (-10.5, 35.0, 34.5, 71.5)


def window_bounds():
    lon0, lon1, lat0, lat1 = WINDOW
    pts = [project(lon0 + (lon1 - lon0) * i / 60, lat) for i in range(61) for lat in (lat0, lat1)]
    pts += [project(lon, lat0 + (lat1 - lat0) * i / 60) for i in range(61) for lon in (lon0, lon1)]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), max(xs), min(ys), max(ys)


def draw_map(ax, shapes, values: dict[str, int], title: str) -> None:
    ax.set_facecolor(SURFACE)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.grid(False)
    for name, rings in shapes.items():
        if TOPO_NAMES.get(name) in EU27:
            continue
        for r in rings:
            if len(r) >= 3:
                ax.add_patch(MplPolygon(r, closed=True, facecolor=OUTSIDE, edgecolor="#e0e4e5", linewidth=0.5, zorder=1))
    for name, rings in shapes.items():
        cc = TOPO_NAMES.get(name)
        if cc not in EU27:
            continue
        colour = bin_colour(values.get(cc, 0))
        best = (0.0, None)
        for r in rings:
            if len(r) < 3:
                continue
            ax.add_patch(MplPolygon(r, closed=True, facecolor=colour, edgecolor=SURFACE, linewidth=0.9, zorder=2))
            a, c = area_centroid(r)
            if a > best[0]:
                best = (a, c)
        if best[1] and (best[0] >= LABEL_MIN_AREA or cc in LABEL_ALWAYS):
            dx, dy = NUDGE.get(cc, (0.0, 0.0))
            dark = colour in RAMP[2:]
            ax.text(best[1][0] + dx, best[1][1] + dy, f"{values.get(cc, 0):,}", ha="center", va="center",
                    fontsize=11, fontweight="semibold", color=SURFACE if dark else INK, zorder=4)
    # Malta is below the 110m resolution: a dot in its colour
    mx, my = project(*MALTA)
    ax.scatter([mx], [my], s=40, color=bin_colour(values.get("MT", 0)), edgecolor=INK_MUTED, linewidth=0.6, zorder=3)
    x0, x1, y0, y1 = window_bounds()
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_title(title, fontsize=14, loc="left", pad=10)


def make_pathway_set(tab, release: str, out: Path) -> Path:
    """One EU map per removal pathway, same colour scale on every map; the
    eighth slot carries the legend and the reading note."""
    shapes = load_shapes()
    fig, axes = plt.subplots(2, 4, figsize=(19, 10.6))
    fig.subplots_adjust(left=0.01, right=0.99, top=0.88, bottom=0.07, wspace=0.03, hspace=0.24)
    for ax, (pw, label) in zip(axes.flat, PATHWAY_PANELS):
        v = {cc: tab[cc][pw] for cc in EU27}
        draw_map(ax, shapes, v, f"{label}\n{sum(v.values())} companies in {n_states(v)} of 27 member states")
    lax = axes.flat[len(PATHWAY_PANELS)]
    lax.axis("off")
    lax.grid(False)
    handles = [Patch(facecolor=ZERO, edgecolor=SURFACE, label="no company")]
    handles += [Patch(facecolor=RAMP[i + 1], edgecolor=SURFACE, label=label) for i, (_lo, _hi, label) in enumerate(COMPANY_BINS)]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.02, 0.98), bbox_transform=lax.transAxes,
               fontsize=13, frameon=False, handlelength=1.4, handleheight=1.1, borderaxespad=0.0, labelspacing=0.4,
               title="Companies per member state", title_fontsize=13, alignment="left")
    narrow_v = {cc: narrow(t) for cc, t in tab.items()}
    other_v = {cc: permanent(t) - narrow(t) for cc, t in tab.items()}
    perm_v = {cc: permanent(t) for cc, t in tab.items()}
    note = (f"{sum(perm_v.values())} EU27 companies have a removal pathway,\nin {n_states(perm_v)} of the 27 member states; "
            f"{27 - n_states(perm_v)} member\nstates have no published company yet.\n\n"
            f"BioCCS and DACCS: {sum(narrow_v.values())} companies in {n_states(narrow_v)} member\nstates. "
            f"The five other pathways: {sum(other_v.values())} companies\nin {n_states(other_v)} member states, "
            f"{sum(t['Biochar'] for t in tab.values())} of them biochar.")
    lax.text(0.02, 0.50, note, transform=lax.transAxes, ha="left", va="top", fontsize=13, color=INK, linespacing=1.4)
    fig.suptitle("EU27 carbon removal companies, one map per pathway", x=0.012, ha="left", fontsize=24,
                 fontweight="semibold", y=0.985)
    fig.text(0.012, 0.025,
             f"Published companies by primary pathway, Captain Drawdown Data release {release}; enabling technology "
             f"({sum(t[ENABLING] for t in tab.values())} EU27 companies) is not a removal pathway and is not shown. "
             "Map: Natural Earth.", fontsize=11, color=INK_MUTED, ha="left", va="bottom")
    return save(fig, out, release)


# ── bars ──────────────────────────────────────────────────────────────

def member_state_order(tab) -> list[str]:
    """Most companies first; the states without a company at the end, A to Z."""
    rows = sorted(EU27, key=lambda cc: (-permanent(tab[cc]), -narrow(tab[cc]), NAMES[cc]))
    with_co = [cc for cc in rows if permanent(tab[cc]) > 0]
    return with_co + sorted((cc for cc in rows if permanent(tab[cc]) == 0), key=lambda cc: NAMES[cc])


def make_bars(tab, researchers, release: str, out: Path) -> Path:
    order = member_state_order(tab)
    n_with = sum(1 for cc in order if permanent(tab[cc]) > 0)
    n = len(order)
    fig, ax = plt.subplots(figsize=(13, 15))
    y = list(range(n))[::-1]
    nar = [narrow(tab[cc]) for cc in order]
    oth = [permanent(tab[cc]) - narrow(tab[cc]) for cc in order]
    tot = [permanent(tab[cc]) for cc in order]
    h = 0.66
    ax.barh(y, nar, height=h, color=PETROL, label="BioCCS and DACCS", zorder=3)
    ax.barh(y, oth, left=nar, height=h, color=RAMP[1],
            label="Biochar, enhanced weathering, mineralisation,\nocean CDR, biomass burial", zorder=3)
    xmax = max(tot)
    for yi, a, t in zip(y, nar, tot):
        if a >= 2:
            ax.text(a / 2, yi, str(a), ha="center", va="center", fontsize=13, color=SURFACE, fontweight="semibold", zorder=4)
        ax.text(t + xmax * 0.012 if t else xmax * 0.012, yi, str(t), ha="left", va="center", fontsize=14,
                color=INK if t else INK_MUTED, zorder=4)
    # researchers column at the right, its header inside the axes above the first row
    col_x = xmax * 1.34
    ax.text(col_x, n + 0.05, "CDR\nresearchers", ha="right", va="bottom", fontsize=13, color=INK_MUTED)
    for yi, cc in zip(y, order):
        ax.text(col_x, yi, f"{researchers.get(cc, 0):,}", ha="right", va="center", fontsize=13, color=INK_MUTED)
    # separator before the member states without a published company
    if n_with < n:
        ysep = y[n_with - 1] - 0.5
        ax.axhline(ysep, color=LINE, linewidth=1.0, zorder=2)
        ax.text(xmax * 0.09, ysep - 0.5, "no published company yet, but a research base in every one of them",
                fontsize=12, color=INK_MUTED, va="center", style="italic")
    ax.set_yticks(y)
    ax.set_yticklabels([NAMES[cc] for cc in order], fontsize=14)
    ax.set_xlim(0, col_x * 1.02)
    ax.set_ylim(-0.7, n + 1.4)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    ax.set_xlabel(f"Published carbon removal companies, release {release}", fontsize=14)
    ax.tick_params(axis="x", labelsize=13)
    ax.set_title("EU27 carbon removal companies by member state\n"
                 f"{sum(tot)} companies with a removal pathway in {n_with} of 27 member states, "
                 f"{sum(nar)} of them in BioCCS and DACCS", fontsize=19, loc="left", pad=14)
    # Figure legend in the open space right of the short bars.
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper left", bbox_to_anchor=(0.30, 0.74), bbox_transform=ax.transAxes,
               fontsize=13, frameon=False, handlelength=1.4)
    fig.text(0.01, 0.03, "Primary pathway per company; enabling technology not counted. Researchers: CDR Researcher Census, "
             "authors of carbon removal papers since 2021.", fontsize=11, color=INK_MUTED, ha="left", va="bottom")
    fig.subplots_adjust(left=0.13, right=0.98, top=0.93, bottom=0.10)
    return save(fig, out, release)


# ── table ─────────────────────────────────────────────────────────────

def write_table(tab, researchers, out: Path) -> Path:
    cols = list(PERMANENT) + [ENABLING]
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["country_code", "member_state", "bioccs_daccs", "every_removal_pathway", "all_published_companies",
                    *[c.lower().replace(" ", "_") for c in cols], "cdr_researchers"])
        for cc in member_state_order(tab):
            t = tab[cc]
            w.writerow([cc, NAMES[cc], narrow(t), permanent(t), sum(t.values()), *[t[c] for c in cols],
                        researchers.get(cc, 0)])
    return out


# ── style ─────────────────────────────────────────────────────────────

def apply_style() -> None:
    families = {f.name for f in font_manager.fontManager.ttflist}
    sans = ["Inter"] if "Inter" in families else ["Helvetica Neue", "Arial"]
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": sans + ["DejaVu Sans"],
        "font.size": 18,
        "axes.titleweight": "semibold",
        "axes.titlelocation": "left",
        "axes.labelcolor": INK_MUTED,
        "axes.edgecolor": LINE,
        "axes.linewidth": 1.0,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.facecolor": SURFACE,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": LINE,
        "grid.linewidth": 0.8,
        "xtick.color": INK_MUTED,
        "ytick.color": INK,
        "text.color": INK,
        "figure.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "legend.frameon": False,
    })


def save(fig, path: Path, release: str) -> Path:
    """Save with a muted source line in the bottom-right corner."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.text(0.995, 0.008, f"captaindrawdown.com/data · release {release}", ha="right", va="bottom",
             fontsize=11, color=INK_MUTED)
    fig.savefig(path, dpi=150, facecolor=SURFACE, edgecolor="none", bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--release", default="2026-11.4", help="release folder under v1/, or 'latest' (default: 2026-11.4)")
    ap.add_argument("--out", default=".", help="output directory (default: current directory)")
    args = ap.parse_args()
    data = REPO / "v1" / args.release
    if not (data / "companies.csv").exists():
        print(f"no release folder {data}")
        return 2
    release = json.loads((data / "manifest.json").read_text(encoding="utf-8"))["version"]
    out_dir = Path(args.out)
    apply_style()
    tab = load_companies(data)
    researchers = load_researchers(data)
    for pw, label in PATHWAY_PANELS:
        v = {cc: tab[cc][pw] for cc in EU27}
        print(f"{label:<20} {sum(v.values()):>4} companies in {n_states(v):>2} member states")
    print(make_pathway_set(tab, release, out_dir / "eu27-companies-one-map-per-pathway.png"))
    print(make_bars(tab, researchers, release, out_dir / "eu27-companies-by-member-state.png"))
    print(write_table(tab, researchers, out_dir / "eu27-companies-by-member-state.csv"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
