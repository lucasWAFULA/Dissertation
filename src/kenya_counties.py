"""
Reference data for all 47 Kenya counties: canonical names and approximate centroids (lat, lon).
Used so the dashboard map can show every county even when data is missing for some.
Names match common variants (e.g. WFP admin2, "Meru North" -> Meru where applicable).
"""
from __future__ import annotations

# All 47 Kenya counties (official names) with approximate centroid (latitude, longitude).
# Sources: public maps and county seats; used for scatter_geo when no shapefile is present.
KENYA_47_COUNTIES: list[tuple[str, float, float]] = [
    ("Baringo", 0.47, 35.95),
    ("Bomet", -0.78, 35.34),
    ("Bungoma", 0.57, 34.56),
    ("Busia", 0.46, 34.09),
    ("Elgeyo Marakwet", 0.52, 35.52),
    ("Embu", -0.54, 37.45),
    ("Garissa", -0.45, 39.64),
    ("Homa Bay", -0.53, 34.46),
    ("Isiolo", 0.35, 37.58),
    ("Kajiado", -2.10, 36.78),
    ("Kakamega", 0.28, 34.75),
    ("Kericho", -0.37, 35.28),
    ("Kiambu", -1.17, 36.82),
    ("Kilifi", -3.63, 39.85),
    ("Kirinyaga", -0.50, 37.32),
    ("Kisii", -0.68, 34.77),
    ("Kisumu", -0.09, 34.75),
    ("Kitui", -1.37, 38.01),
    ("Kwale", -4.18, 39.45),
    ("Laikipia", 0.20, 36.90),
    ("Lamu", -2.27, 40.90),
    ("Machakos", -1.52, 37.27),
    ("Makueni", -2.00, 37.65),
    ("Mandera", 3.94, 41.86),
    ("Marsabit", 2.33, 37.99),
    ("Meru", -0.05, 37.65),
    ("Migori", -1.06, 34.47),
    ("Mombasa", -4.04, 39.67),
    ("Murang'a", -0.72, 37.15),
    ("Nairobi", -1.29, 36.82),
    ("Nakuru", -0.30, 36.07),
    ("Nandi", -0.18, 35.13),
    ("Narok", -1.08, 35.87),
    ("Nyamira", -0.57, 34.95),
    ("Nyandarua", -0.24, 36.52),
    ("Nyeri", -0.42, 36.95),
    ("Samburu", 1.10, 36.70),
    ("Siaya", -0.06, 34.29),
    ("Taita Taveta", -3.40, 38.36),
    ("Tana River", -1.50, 40.00),
    ("Tharaka Nithi", -0.30, 37.65),
    ("Trans Nzoia", 1.02, 34.95),
    ("Turkana", 3.12, 35.60),
    ("Uasin Gishu", 0.52, 35.27),
    ("Vihiga", -0.08, 34.72),
    ("Wajir", 1.75, 40.06),
    ("West Pokot", 1.52, 35.25),
]

# Normalized name -> (lat, lon) for lookup; include common variants from data (e.g. "Meru North" -> Meru).
def get_kenya_county_centroids() -> dict[str, tuple[float, float]]:
    out: dict[str, tuple[float, float]] = {}
    for name, lat, lon in KENYA_47_COUNTIES:
        out[name.strip()] = (lat, lon)
    # Variants often seen in WFP / admin data
    variants = [
        ("Meru North", "Meru"),
        ("Muranga", "Murang'a"),
        ("Tharaka", "Tharaka Nithi"),
        ("Transzoia", "Trans Nzoia"),
        ("West Pokot", "West Pokot"),
        ("Homabay", "Homa Bay"),
        ("Taita Taveta", "Taita Taveta"),
        ("Tana River", "Tana River"),
    ]
    for alias, canonical in variants:
        if canonical in out and alias not in out:
            out[alias] = out[canonical]
    return out


def get_all_47_county_names() -> list[str]:
    return [name for name, _, _ in KENYA_47_COUNTIES]


def data_county_to_canonical(name: str) -> str | None:
    """Map a county name from data (e.g. WFP) to one of the 47 canonical names, or None."""
    if not name or not isinstance(name, str):
        return None
    s = name.strip()
    canonical = get_all_47_county_names()
    if s in canonical:
        return s
    # One-way variants: data name -> canonical
    variants: list[tuple[str, str]] = [
        ("meru north", "Meru"),
        ("muranga", "Murang'a"),
        ("tharaka", "Tharaka Nithi"),
        ("transzoia", "Trans Nzoia"),
        ("homabay", "Homa Bay"),
        ("taita-taveta", "Taita Taveta"),
        ("taita taveta", "Taita Taveta"),
        ("elgeyo-marakwet", "Elgeyo Marakwet"),
        ("tharaka-nithi", "Tharaka Nithi"),
        ("trans nzoia", "Trans Nzoia"),
        ("west pokot", "West Pokot"),
    ]
    lower = s.lower()
    for data_name, can in variants:
        if data_name in lower or lower in data_name:
            return can
    for c in canonical:
        if c.lower() in lower or lower in c.lower():
            return c
    return None
