"""Ciudades en cobertura Grupo Sazón (España y México).

Fuente de verdad operativa: `backend/docs/GRUPO_SAZON_PUBLIC_INFO_ES.txt`.
La lista aquí debe mantenerse alineada con ese documento.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from typing import FrozenSet, Optional

# España — mismo orden que el doc público
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

# México — mismo orden que el doc público
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
    """Lowercase, strip accents, collapse whitespace — para comparar etiquetas."""

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
    """True si `city_zone` coincide con alguna ciudad listada (tras normalizar).

    Acepta valores del tipo "Guadalajara, Jalisco" usando el primer segmento
    antes de coma, punto y coma o barra.
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
        # "Guadalajara centro", " Zona norte Monterrey" — ciudad como prefijo/sufijo corto
        for a in allowed:
            if len(a) < 3:
                continue
            if n.startswith(a + " ") or n.endswith(" " + a):
                return True

    return False
