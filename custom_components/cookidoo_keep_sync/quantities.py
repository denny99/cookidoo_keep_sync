"""Parser + Aggregator für Cookidoo-Mengenangaben.

Beispiele:
    aggregate(["70 g", "0.5 kg"])             -> "570 g"
    aggregate(["1 EL", "2 TL"])               -> "1 EL + 2 TL"  (gemischt innerhalb spoon)
    aggregate(["1 Stk", "2 Stk"])             -> "3 Stk"
    aggregate(["70 g", "1 Stk"])              -> "70 g + 1 Stk"
    aggregate(["1/2 TL", "1 Prise"])          -> "0,5 TL + 1 Prise"
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Einheitengruppen mit Faktor zur kanonischen Einheit der Gruppe (kleinste Einheit)
_GROUPS: dict[str, dict[str, float]] = {
    "mass": {
        "mg": 0.001, "g": 1.0, "gr": 1.0, "gramm": 1.0, "kg": 1000.0,
    },
    "volume": {
        "ml": 1.0, "cl": 10.0, "dl": 100.0, "l": 1000.0, "liter": 1000.0,
    },
    "spoon": {
        "tl": 1.0, "teelöffel": 1.0,
        "el": 3.0, "esslöffel": 3.0,
    },
}
_UNIT_TO_GROUP = {u: g for g, units in _GROUPS.items() for u in units}

# Bevorzugte Einheit pro Gruppe für die Anzeige (größte zuerst)
_GROUP_DISPLAY: dict[str, list[tuple[str, float]]] = {
    "mass":   [("kg", 1000.0), ("g", 1.0)],
    "volume": [("l", 1000.0), ("ml", 1.0)],
    "spoon":  [("EL", 3.0), ("TL", 1.0)],
}

# Zähleinheiten: Synonyme/Plurale auf eine kanonische Schreibweise normalisieren.
_COUNT_NORM: dict[str, str] = {
    "stk": "Stk", "stück": "Stk", "stueck": "Stk",
    "pck": "Pck", "packung": "Pck", "packungen": "Pck",
    "dose": "Dose", "dosen": "Dose",
    "glas": "Glas", "gläser": "Glas",
    "flasche": "Flasche", "flaschen": "Flasche",
    "becher": "Becher",
    "bund": "Bund",
    "prise": "Prise", "prisen": "Prise",
    "msp": "Msp.",
    "zehe": "Zehe", "zehen": "Zehe",
    "scheibe": "Scheibe", "scheiben": "Scheibe",
    "stange": "Stange", "stangen": "Stange",
    "blatt": "Blatt", "blätter": "Blatt",
    "zweig": "Zweig", "zweige": "Zweig",
    "kopf": "Kopf", "köpfe": "Kopf",
    "tasse": "Tasse", "tassen": "Tasse",
}

_QTY_RE = re.compile(
    r"^\s*"
    r"(?P<n1>\d+(?:[.,]\d+)?(?:\s*/\s*\d+(?:[.,]\d+)?)?)"
    r"(?:\s*[-–]\s*(?P<n2>\d+(?:[.,]\d+)?(?:\s*/\s*\d+)?))?"
    r"(?:\s*(?P<unit>[a-zA-ZäöüÄÖÜß.]+))?"
    r"\s*$",
    re.IGNORECASE,
)

# Trailing-Qty in einem Item-Summary erkennen, z.B. "Zwiebeln 70 g"
_TRAILING_QTY_RE = re.compile(
    r"^(?P<name>.+?)[\s,]+"
    r"(?P<qty>"
    r"\d+(?:[.,]\d+)?(?:\s*/\s*\d+)?(?:\s*[-–]\s*\d+(?:[.,]\d+)?)?"
    r"(?:\s*[a-zA-ZäöüÄÖÜß.]+)?"
    r")\s*$",
    re.IGNORECASE,
)


@dataclass
class _Quantity:
    """Geparste Mengenangabe. Privat — externe Module nutzen `aggregate`."""
    amount: float
    unit: str       # normalisiert: lowercase, ohne Punkt
    unit_raw: str   # Original-Casing wie eingegeben (für Display unbekannter Einheiten)
    raw: str        # ungeparster Originaltext


def split_name_qty(summary: str) -> tuple[str, str]:
    """Zerlegt 'Zwiebeln 70 g' → ('Zwiebeln', '70 g').
    Splittet nur, wenn der erkannte qty-Teil eine bekannte Einheit hat,
    damit Bezeichnungen wie 'Mehl Type 405' nicht zerlegt werden."""
    s = summary.strip()
    m = _TRAILING_QTY_RE.match(s)
    if not m:
        return s, ""
    qty = m.group("qty").strip()
    parsed = parse_qty(qty)
    if parsed is None:
        return s, ""
    if not parsed.unit or (
        parsed.unit not in _UNIT_TO_GROUP and parsed.unit not in _COUNT_NORM
    ):
        return s, ""
    return m.group("name").strip(), qty


def parse_qty(text: str) -> _Quantity | None:
    if not text:
        return None
    m = _QTY_RE.match(text.strip())
    if not m:
        return None
    a1 = _parse_num(m.group("n1"))
    if a1 is None:
        return None
    a2 = _parse_num(m.group("n2")) if m.group("n2") else None
    amount = max(a1, a2) if a2 is not None else a1
    unit_raw = (m.group("unit") or "").strip(".")
    unit = unit_raw.lower()
    return _Quantity(amount=amount, unit=unit, unit_raw=unit_raw, raw=text.strip())


def aggregate(quantities: list[str]) -> str:
    """Aggregiert eine Liste roher Mengenangaben zu einem kompakten Display-String."""
    qs = [q for q in quantities if q and q.strip()]
    if not qs:
        return ""

    by_group_total: dict[str, float] = {}  # group -> total in kanonischer Einheit
    by_count_total: dict[str, float] = {}  # Display-Unit-Name -> total
    unparseable: list[str] = []

    for raw in qs:
        p = parse_qty(raw)
        if p is None:
            if raw.strip() not in unparseable:
                unparseable.append(raw.strip())
            continue
        group = _UNIT_TO_GROUP.get(p.unit)
        if group:
            factor = _GROUPS[group][p.unit]
            by_group_total[group] = by_group_total.get(group, 0.0) + p.amount * factor
        else:
            # Bekannte Zähleinheit → kanonische Schreibweise; sonst Original-Casing
            unit_display = (
                _COUNT_NORM.get(p.unit) if p.unit else ""
            ) or p.unit_raw
            by_count_total[unit_display] = (
                by_count_total.get(unit_display, 0.0) + p.amount
            )

    parts: list[str] = []

    for group, total in by_group_total.items():
        unit, amount = _pick_display_unit(group, total)
        parts.append(f"{_fmt_num(amount)} {unit}")

    for unit, total in by_count_total.items():
        if unit:
            parts.append(f"{_fmt_num(total)} {unit}")
        else:
            parts.append(_fmt_num(total))

    parts.extend(unparseable)
    return " + ".join(parts)


def _pick_display_unit(group: str, canonical_total: float) -> tuple[str, float]:
    for unit, factor in _GROUP_DISPLAY[group]:
        if canonical_total >= factor:
            return unit, canonical_total / factor
    smallest_unit, smallest_factor = _GROUP_DISPLAY[group][-1]
    return smallest_unit, canonical_total / smallest_factor


def _parse_num(s: str) -> float | None:
    s = s.replace(" ", "").replace(",", ".")
    if "/" in s:
        try:
            num, denom = s.split("/")
            d = float(denom)
            return float(num) / d if d else None
        except (ValueError, ZeroDivisionError):
            return None
    try:
        return float(s)
    except ValueError:
        return None


def _fmt_num(x: float) -> str:
    if abs(x - round(x)) < 1e-9:
        return str(int(round(x)))
    return f"{x:.2f}".rstrip("0").rstrip(".").replace(".", ",")


# Helper für Dedup-Vergleich: entfernt trailing "(...)" aus einem Keep-Summary,
# damit "Zwiebeln" und "Zwiebeln (70 g)" als dasselbe Item gelten.
_PARENS_TAIL_RE = re.compile(r"\s*\([^)]*\)\s*$")


def normalize_for_dedup(summary: str) -> str:
    s = strip_qty_parens(summary).lower()
    return re.sub(r"\s+", " ", s)


def strip_qty_parens(summary: str) -> str:
    """Entfernt nur den von uns angehängten '(qty)'-Teil am Ende. Case bleibt erhalten."""
    return _PARENS_TAIL_RE.sub("", summary).strip()
