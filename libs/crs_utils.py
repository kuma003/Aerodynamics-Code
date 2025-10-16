# crs_utils.py - Coordinate Reference System (CRS) utilities.

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Literal, Optional, Sequence, Tuple, Union

import math
import tomllib

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "configs" / "crs.toml"

# 東京近郊にある射場を想定した仮の座標（lat, lon）。
DEFAULT_SITE_COORD: Tuple[float, float] = (35.6176, 139.7867)


@dataclass(frozen=True, slots=True)
class CRSBase:
    name_jp: str
    name_en: str

    def display_label(self, lng: Literal["jp", "en"] = "jp") -> str:
        match lng:
            case "jp":
                return self.name_jp.strip()
            case "en":
                return self.name_en.strip()
            case _:
                return CRSBase.display_label(self)


# Backwards compatibility alias (older code may import CRS_base).
CRS_base = CRSBase


@dataclass(frozen=True, slots=True)
class GCS(CRSBase):
    epsg: int


@dataclass(frozen=True, slots=True)
class ProjectedCRSVariant(CRSBase):
    epsg: Optional[int]
    lat: Optional[float] = None
    lon: Optional[float] = None
    lon_min: Optional[float] = None
    lon_max: Optional[float] = None

    def score_for_coordinate(self, coord: Tuple[float, float]) -> float:
        lat, lon = coord
        score: Optional[float] = None

        if self.lat is not None and self.lon is not None:
            score = math.hypot(lat - self.lat, lon - self.lon)

        if self.lon_min is not None and self.lon_max is not None:
            if self.lon_min <= lon <= self.lon_max:
                range_score = 0.0
            else:
                range_score = min(abs(lon - self.lon_min), abs(lon - self.lon_max))
            score = range_score if score is None else min(score, range_score)

        if score is None:
            score = 1e6

        return score


@dataclass(frozen=True, slots=True)
class ProjectedCRS(CRSBase):
    type: str
    epsg: Optional[int]
    variants: Tuple[ProjectedCRSVariant, ...] = field(default_factory=tuple)

    def display_label(self) -> str:
        return CRSBase.display_label(self)

    def best_variant_for_coordinate(
        self, coord: Tuple[float, float]
    ) -> Optional[ProjectedCRSVariant]:
        if not self.variants:
            return None
        return min(
            self.variants, key=lambda variant: variant.score_for_coordinate(coord)
        )


@dataclass(frozen=True, slots=True)
class CRSCatalog:
    gcs: Tuple[GCS, ...]
    projected: Tuple[ProjectedCRS, ...]


class CRSCatalogError(Exception):
    """Raised when the CRS catalog fails to load."""


_JPRCS_RANGES = {
    "JGD2011": (6669, 6687),
    "JGD2000": (2243, 2461),
}

_UTM_RANGES = {
    "JGD2011": (6688, 6692),
    "JGD2000": (3097, 3101),
}


def load_crs_catalog(path: Optional[Path] = None) -> CRSCatalog:
    target_path = Path(path) if path else _CONFIG_PATH

    try:
        raw_text = target_path.read_text(encoding="utf-8")
    except OSError as exc:  # pragma: no cover - thin wrapper
        raise CRSCatalogError(f"Failed to read CRS configuration: {exc}") from exc

    try:
        data = tomllib.loads(raw_text)
    except tomllib.TOMLDecodeError as exc:  # pragma: no cover - thin wrapper
        raise CRSCatalogError(f"Invalid CRS configuration: {exc}") from exc

    crs_entries = data.get("crs")
    if not isinstance(crs_entries, list):
        raise CRSCatalogError("[crs] section is missing or invalid.")

    gcs_entries: list[GCS] = []
    projected_entries: list[ProjectedCRS] = []

    jprcs_variants = _parse_jprcs_entries(data.get("JPRCS", []))
    utm_variants = _parse_utm_entries(data.get("UTM", []))

    for entry in crs_entries:
        if not isinstance(entry, dict):
            continue

        name_jp = _ensure_str(entry.get("name_jp"))
        name_en = _ensure_str(entry.get("name_en"))
        type_raw = _ensure_str(entry.get("type"))
        epsg_value = entry.get("epsg")
        epsg = int(epsg_value) if isinstance(epsg_value, int) else None

        type_norm = type_raw.lower()
        if type_norm == "gcs":
            if epsg is None:
                continue
            gcs_entries.append(GCS(name_jp=name_jp, name_en=name_en, epsg=epsg))
            continue

        variants: Tuple[ProjectedCRSVariant, ...] = tuple()
        if type_norm == "jprcs":
            variants = _filter_variants_by_name(name_en, jprcs_variants, _JPRCS_RANGES)
        elif type_norm == "utm":
            variants = _filter_variants_by_name(name_en, utm_variants, _UTM_RANGES)

        if not variants:
            variant = ProjectedCRSVariant(name_jp=name_jp, name_en=name_en, epsg=epsg)
            variants = (variant,)

        projected_entries.append(
            ProjectedCRS(
                name_jp=name_jp,
                name_en=name_en,
                type=type_raw,
                epsg=epsg,
                variants=variants,
            )
        )

    if not gcs_entries and not projected_entries:
        raise CRSCatalogError("No CRS entries found in configuration.")

    return CRSCatalog(gcs=tuple(gcs_entries), projected=tuple(projected_entries))


def choose_geographic_crs(catalog: Sequence[GCS]) -> Optional[GCS]:
    if not catalog:
        return None

    preferred_names = {"JGD2011", "JGD2000", "WGS84"}
    for preferred in preferred_names:
        for entry in catalog:
            if preferred in {entry.name_en, entry.name_jp}:
                return entry
    return catalog[0]


def choose_projected_group(
    catalog: Sequence[ProjectedCRS],
    coord: Tuple[float, float] = DEFAULT_SITE_COORD,
) -> Optional[Tuple[ProjectedCRS, ProjectedCRSVariant]]:
    best_pair: Optional[Tuple[ProjectedCRS, ProjectedCRSVariant]] = None
    best_score = float("inf")

    for group in catalog:
        variant = group.best_variant_for_coordinate(coord)
        if variant is None:
            continue
        score = variant.score_for_coordinate(coord)
        if score < best_score:
            best_score = score
            best_pair = (group, variant)

    return best_pair


def _parse_jprcs_entries(
    raw_entries: Iterable[dict],
) -> Tuple[ProjectedCRSVariant, ...]:
    variants: list[ProjectedCRSVariant] = []
    for entry in raw_entries:
        if not isinstance(entry, dict):
            continue
        epsg = entry.get("epsg")
        try:
            epsg_int = int(epsg)
        except (TypeError, ValueError):
            continue

        variants.append(
            ProjectedCRSVariant(
                name_jp=_ensure_str(entry.get("name_jp")),
                name_en=_ensure_str(entry.get("name_en")),
                epsg=epsg_int,
                lat=_to_float(entry.get("lat")),
                lon=_to_float(entry.get("lon")),
            )
        )
    return tuple(variants)


def _parse_utm_entries(raw_entries: Iterable[dict]) -> Tuple[ProjectedCRSVariant, ...]:
    variants: list[ProjectedCRSVariant] = []
    for entry in raw_entries:
        if not isinstance(entry, dict):
            continue
        epsg = entry.get("epsg")
        try:
            epsg_int = int(epsg)
        except (TypeError, ValueError):
            continue

        variants.append(
            ProjectedCRSVariant(
                name_jp=_ensure_str(entry.get("name_jp")),
                name_en=_ensure_str(entry.get("name_en")),
                epsg=epsg_int,
                lon_min=_to_float(entry.get("lon_min")),
                lon_max=_to_float(entry.get("lon_max")),
            )
        )
    return tuple(variants)


def _filter_variants_by_name(
    name_en: str,
    variants: Sequence[ProjectedCRSVariant],
    ranges: dict[str, Tuple[int, int]],
) -> Tuple[ProjectedCRSVariant, ...]:
    if not variants:
        return tuple()

    key = name_en.strip() or ""
    span = ranges.get(key)
    if span is None:
        return tuple()

    start, end = span
    matched = [
        variant
        for variant in variants
        if variant.epsg is not None and start <= variant.epsg <= end
    ]
    return tuple(matched)


def _ensure_str(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if value is None:
        return ""
    return str(value).strip()


def _to_float(value: object) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


__all__ = [
    "CRSBase",
    "CRS_base",
    "GCS",
    "ProjectedCRS",
    "ProjectedCRSVariant",
    "CRSCatalog",
    "CRSCatalogError",
    "DEFAULT_SITE_COORD",
    "choose_geographic_crs",
    "choose_projected_group",
    "load_crs_catalog",
]
