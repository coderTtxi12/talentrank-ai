"""Grupo Sazón coverage cities (Spain and Mexico).

Operational source of truth: `backend/docs/GRUPO_SAZON_PUBLIC_INFO_ES.txt`.
Keep this module’s tuples aligned with that document.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from typing import FrozenSet, Optional

# Spain — same order as the public reference doc
COVERAGE_CITIES_SPAIN: tuple[str, ...] = (
    "Madrid",
    "Barcelona",
    "Valencia",
    "Sevilla",
    "Malaga",
    "Zaragoza",
    "Bilbao",
    "Alicante",
    "Murcia",
    "Palma",
    "Las Palmas",
    "Cordoba",
    "Valladolid",
    "Vigo",
    "Gijon",
    "A Coruna",
    "Granada",
    "Pamplona",
    "Donostia-San Sebastian",
    "Salamanca",
)

# Mexico — same order as the public reference doc
COVERAGE_CITIES_MEXICO: tuple[str, ...] = (
    "Ciudad de Mexico",
    "Guadalajara",
    "Monterrey",
    "Puebla",
    "Queretaro",
    "Tijuana",
    "Leon",
    "Merida",
    "Toluca",
    "San Luis Potosi",
    "Chihuahua",
    "Aguascalientes",
    "Mexicali",
    "Saltillo",
    "Hermosillo",
    "Morelia",
    "Veracruz",
    "Cancun",
    "Cuernavaca",
    "Culiacan",
    "Oaxaca",
    "Tuxtla Gutierrez",
    "Torreon",
    "Reynosa",
    "Tampico",
)


def normalize_city_label(value: str) -> str:
    """Lowercase, strip accents, collapse whitespace — for label comparison."""

    s = value.strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = re.sub(r"\s+", " ", s).strip()
    return s


@lru_cache
def _normalized_coverage_set() -> FrozenSet[str]:
    combined = COVERAGE_CITIES_SPAIN + COVERAGE_CITIES_MEXICO
    return frozenset(normalize_city_label(c) for c in combined)


def city_zone_in_coverage(city_zone: Optional[str]) -> bool:
    """True if `city_zone` matches a listed city after normalization.

    Accepts values like 'Guadalajara, Jalisco' by taking the first segment
    before comma, semicolon, or slash.
    """

    if city_zone is None:
        return False
    raw = city_zone.strip()
    if not raw:
        return False

    allowed = _normalized_coverage_set()

    segments: list[str] = [raw]
    for sep in (",", ";", "/"):
        if sep in raw:
            first = raw.split(sep, 1)[0].strip()
            if first:
                segments.append(first)
            break

    for seg in segments:
        n = normalize_city_label(seg)
        if n in allowed:
            return True
        # "Guadalajara centro", " Zona norte Monterrey" — city as short prefix/suffix
        for a in allowed:
            if len(a) < 3:
                continue
            if n.startswith(a + " ") or n.endswith(" " + a):
                return True

    return False
