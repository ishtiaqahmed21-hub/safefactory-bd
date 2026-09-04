"""Shared chart theme and data loading for the SafeFactory BD dashboard.

The palette is a validated categorical set: hues are assigned to slots in a
fixed order and never cycled, sequential encodings use a single hue light to
dark, and the four status colours are reserved for state and never reused as a
series colour. Status colours always ship with a text label beside them, so
meaning is never carried by hue alone.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from safefactory.config import PROCESSED, REFERENCE  # noqa: E402

# --------------------------------------------------------------------------
# Palette
# --------------------------------------------------------------------------
# Categorical slots, fixed order. Slots 1-3 are the only ones used where every
# pair can appear together (scatter, maps); beyond three, series fold into
# "Other" or the chart is faceted.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]

# Sequential ramp, one hue, light to dark. Used for magnitude only.
SEQ_BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

# Status palette. Reserved for state; never a series colour.
STATUS = {
    "good": "#0ca30c",
    "warning": "#fab219",
    "serious": "#ec835a",
    "critical": "#d03b3b",
}

# Risk bands map onto the status palette because a band IS a state.
BAND_COLOR = {
    "Low": STATUS["good"],
    "Medium": STATUS["warning"],
    "High": STATUS["serious"],
    "Critical": STATUS["critical"],
}
BAND_ORDER = ["Low", "Medium", "High", "Critical"]

INDEX_BAND_COLOR = {
    "Low": STATUS["good"],
    "Moderate": STATUS["warning"],
    "Elevated": STATUS["serious"],
    "High": STATUS["critical"],
}

# Chart chrome
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"

FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'


def layout(title: str = "", height: int = 380, **kw) -> dict:
    """Standard Plotly layout: recessive grid and axes, ink-coloured text."""
    base = dict(
        title=dict(text=title, font=dict(size=15, color=INK, family=FONT), x=0, xanchor="left"),
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(family=FONT, color=INK_SECONDARY, size=12),
        height=height,
        margin=dict(l=10, r=10, t=40 if title else 14, b=74),
        xaxis=dict(gridcolor=GRID, linecolor=AXIS, zerolinecolor=AXIS,
                   tickfont=dict(color=INK_MUTED, size=11)),
        yaxis=dict(gridcolor=GRID, linecolor=AXIS, zerolinecolor=AXIS,
                   tickfont=dict(color=INK_MUTED, size=11)),
        # Legend below the plot: above it, a long chart title and the legend
        # row collide at narrow widths.
        legend=dict(orientation="h", yanchor="top", y=-0.26, x=0,
                    font=dict(color=INK_SECONDARY, size=11), bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(font=dict(family=FONT, size=12), bgcolor=SURFACE,
                        bordercolor=AXIS, font_color=INK),
    )
    base.update(kw)
    return base


# --------------------------------------------------------------------------
# Page setup
# --------------------------------------------------------------------------
CSS = """
<style>
  .block-container { padding-top: 2.2rem; max-width: 1350px; }
  .sf-tiles { display: flex; gap: 12px; flex-wrap: wrap; margin: 4px 0 18px 0; }
  .sf-tile {
    flex: 1 1 140px; background: #fcfcfb; border: 1px solid rgba(11,11,11,0.10);
    border-radius: 10px; padding: 14px 16px;
  }
  .sf-tile .lab {
    font-size: 11px; letter-spacing: .04em; text-transform: uppercase;
    color: #898781; margin-bottom: 6px;
  }
  .sf-tile .val { font-size: 26px; font-weight: 650; color: #0b0b0b; line-height: 1.1; }
  .sf-tile .sub { font-size: 11.5px; color: #52514e; margin-top: 5px; }
  .sf-note {
    border-left: 3px solid #2a78d6; background: #f5f8fd; padding: 10px 14px;
    border-radius: 0 8px 8px 0; font-size: 13px; color: #52514e; margin: 6px 0 16px 0;
  }
  .sf-warn {
    border-left: 3px solid #fab219; background: #fdf8ec; padding: 10px 14px;
    border-radius: 0 8px 8px 0; font-size: 13px; color: #52514e; margin: 6px 0 16px 0;
  }
  .sf-crit {
    border-left: 3px solid #d03b3b; background: #fdf1f1; padding: 10px 14px;
    border-radius: 0 8px 8px 0; font-size: 13px; color: #52514e; margin: 6px 0 16px 0;
  }
  h1 { font-size: 27px !important; }
  h2 { font-size: 19px !important; padding-top: .4rem !important; }
  h3 { font-size: 15px !important; }
</style>
"""


def setup(title: str) -> None:
    st.set_page_config(page_title=f"{title} — SafeFactory BD", layout="wide",
                       page_icon="🏭")
    st.markdown(CSS, unsafe_allow_html=True)


def tiles(items: list[tuple[str, str, str]]) -> None:
    """Render a row of stat tiles. Each item is (label, value, sub-caption)."""
    html = '<div class="sf-tiles">'
    for label, value, sub in items:
        html += (
            f'<div class="sf-tile"><div class="lab">{label}</div>'
            f'<div class="val">{value}</div><div class="sub">{sub}</div></div>'
        )
    st.markdown(html + "</div>", unsafe_allow_html=True)


def note(text: str, kind: str = "note") -> None:
    cls = {"note": "sf-note", "warn": "sf-warn", "crit": "sf-crit"}[kind]
    st.markdown(f'<div class="{cls}">{text}</div>', unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Data access
# --------------------------------------------------------------------------
@st.cache_data
def load(name: str, folder: str = "processed") -> pd.DataFrame:
    base = PROCESSED if folder == "processed" else REFERENCE
    path = base / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"{path.name} not found. Run `python scripts/build_dataset.py` first."
        )
    return pd.read_csv(path)


def guard() -> bool:
    """Show a clear message instead of a stack trace if the build has not run."""
    if not (PROCESSED / "hira_scored.csv").exists():
        st.error(
            "Processed data not found. Run **`python scripts/build_dataset.py`** "
            "from the repository root, then reload this page."
        )
        return False
    return True
