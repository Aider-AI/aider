"""Opt-in energy/carbon estimate from cost, using CLEER per-model Wh-per-USD.

Source: CLEER dashboard data (Sustainable AI Group, https://cleerdash.sustainableaigroup.com/),
licensed CC BY-NC 4.0, so it is read from a user-supplied CSV path and never bundled.
Wh = cost_usd x energy_wh_per_usd for the model's Agentic/Typical workload. The band is
+/- the row's energy SD/mean, and gCO2e scales with the row's carbon/energy ratio.
Valid for agentic sessions only (CLEER Chat Wh/USD is ~2.7x higher).
"""

import csv
import re

REQUIRED = (
    "model_name",
    "use_case",
    "tier",
    "energy_wh_mean",
    "energy_wh_sd",
    "carbon_gco2e_mean",
    "energy_wh_per_usd",
)
CLAUDE_RE = re.compile(r"(opus|sonnet|haiku|fable)[\s-]*(\d+)(?:[.-](\d)(?!\d))?", re.I)


def parse_model(name):
    """'claude-opus-4-5', 'Sonnet 4.5' -> ('opus', 4.5); None if not a Claude family name."""
    m = CLAUDE_RE.search(name or "")
    return (m[1].lower(), float(f"{m[2]}.{m[3] or 0}")) if m else None


def name_key(name):
    """Lowercase; drop [..], provider prefixes, -YYYYMMDD, leading 'claude'; '4-5' -> '4.5'."""
    s = re.sub(r"\[[^\]]*\]", "", (name or "").lower()).rsplit("/", 1)[-1]
    s = re.sub(r"-\d{8}\b", "", s)
    s = re.sub(r"(\d)-(\d)(?!\d)", r"\1.\2", s)
    return re.sub(r"^claude ", "", re.sub(r"[^a-z0-9.]+", " ", s).strip())


def load_table(path, use_case="Agentic", tier="Typical"):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [k for k in REQUIRED if k not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"CLEER CSV missing columns: {', '.join(missing)}")
        rows = []
        for r in reader:
            if r["use_case"] != use_case or r["tier"] != tier:
                continue
            try:
                mean = float(r["energy_wh_mean"])
                wh_per_usd = float(r["energy_wh_per_usd"])
                sd = float(r["energy_wh_sd"])
                carbon = float(r["carbon_gco2e_mean"])
            except ValueError:
                continue
            if not (mean > 0 and wh_per_usd > 0):
                continue
            parsed = parse_model(r["model_name"])
            rows.append(
                dict(
                    name=r["model_name"],
                    key=name_key(r["model_name"]),
                    family=parsed[0] if parsed else None,
                    version=parsed[1] if parsed else None,
                    wh_per_usd=wh_per_usd,
                    sd_ratio=sd / mean,
                    g_per_wh=carbon / mean,
                )
            )
    return rows


def match(rows, model):
    """Return (row, proxied). Exact name first; Claude falls back to newest lower same-family."""
    key = name_key(model)
    for r in rows:
        if r["key"] == key:
            return r, False
    want = parse_model(model)
    if not want:
        return None
    fam = sorted(
        (r for r in rows if r["family"] == want[0]), key=lambda r: r["version"], reverse=True
    )
    for r in fam:
        if r["version"] == want[1]:
            return r, False
    near = next((r for r in fam if r["version"] < want[1]), fam[0] if fam else None)
    return (near, True) if near else None


def format_estimate(rows, model, cost, grid_g_per_kwh=None, carbon=True):
    """Single-model estimate; see format_total."""
    return format_total(rows, {model: cost}, grid_g_per_kwh, carbon)


def format_total(rows, costs, grid_g_per_kwh=None, carbon=True):
    """'⚡ ~44-66 Wh · 30-45 gCO₂e' summed over {model: cost}; '~' marks a proxied version.

    Returns '' when no model matches or has cost. Unmatched models are skipped.
    """
    lo = hi = glo = ghi = 0.0
    proxy = found = False
    for model, cost in costs.items():
        m = match(rows, model)
        if not m or not cost or cost <= 0:
            continue
        row, p = m
        wh = cost * row["wh_per_usd"]
        a, b = wh * max(0.0, 1 - row["sd_ratio"]), wh * (1 + row["sd_ratio"])
        g = grid_g_per_kwh / 1000 if grid_g_per_kwh else row["g_per_wh"]
        lo, hi, glo, ghi = lo + a, hi + b, glo + a * g, ghi + b * g
        proxy, found = proxy or p, True
    if not found:
        return ""
    unit, div = ("kWh", 1000) if hi >= 1000 else ("Wh", 1)

    def num(x):
        # integer when >= 10, one decimal below; anything that would show "0.0" is "0"
        return f"{x:.0f}" if round(x, 1) in (0,) or round(x, 1) >= 10 else f"{x:.1f}"

    def band(a, b, div=1):
        a, b = a / div, b / div
        if 0 < b and round(b, 1) == 0:
            return "<0.1"
        fa, fb = num(a), num(b)
        return fa if fa == fb else f"{fa}-{fb}"

    out = f"⚡ {'~' if proxy else ''}{band(lo, hi, div)} {unit}"
    if carbon:
        out += f" · {band(glo, ghi)} gCO₂e"
    return out
