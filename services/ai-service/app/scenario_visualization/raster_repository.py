"""Exact, bounded reads of A20 manifest-selected scenario GeoTIFFs."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from rasterio.io import MemoryFile

from .repository import (
    MAX_RASTER_BYTES,
    InvalidScenarioSelector,
    ScenarioAssetNotFound,
    ScenarioAssetRepository,
    ScenarioAssetsUnavailable,
    ScenarioIdentityConflict,
    _validate_selector,
)


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_BANDS = frozenset({"p05", "p50", "p95"})
_ALLOWED_ROOT = PurePosixPath("data/features/forecast/batch2_v1")


class ScenarioRasterRepository:
    """Read exact original bytes for one saved scenario slice band.

    The manifest and all declared raster references are validated before a
    selected file is read. A second size/hash check is performed on the exact
    response bytes, so a changed file cannot produce a partial response.
    """

    def __init__(self, project_root: Path | None = None) -> None:
        self.assets = ScenarioAssetRepository(project_root)

    def read(
        self, event_id: str, scenario_id: str, valid_time_utc: str, band: str
    ) -> tuple[bytes, dict[str, Any]]:
        _validate_selector(event_id, scenario_id)
        _validate_saved_timestamp(valid_time_utc)
        if band not in _BANDS:
            raise InvalidScenarioSelector("band must be p05, p50, or p95.")

        manifest = self.assets._validated_manifest()
        matches = [
            series for series in manifest["scenario_series"]
            if series["event_id"] == event_id and series["scenario_id"] == scenario_id
        ]
        if not matches:
            raise ScenarioAssetNotFound("No exact saved scenario asset was found.")
        if len(matches) != 1:
            raise ScenarioIdentityConflict("Scenario manifest identity is ambiguous.")

        slices = [
            item for item in matches[0]["slices"]
            if item["valid_time_utc"] == valid_time_utc
        ]
        if not slices:
            raise ScenarioAssetNotFound("No exact saved scenario time was found.")
        if len(slices) != 1:
            raise ScenarioIdentityConflict("Scenario saved-time identity is ambiguous.")

        reference = slices[0]["bands"].get(band)
        if not isinstance(reference, dict):
            raise ScenarioAssetNotFound("No exact saved scenario band was found.")
        if (
            reference.get("dtype") != "float32"
            or reference.get("grid") != manifest["grid"]
            or reference.get("nodata_value") != manifest["nodata"]["value"]
            or reference.get("units") != manifest["depth_units"]["value"]
            or reference.get("band_units_metadata") is not None
        ):
            raise ScenarioAssetsUnavailable("Scenario raster metadata does not match the manifest.")

        relative = PurePosixPath(reference.get("path", ""))
        size = reference.get("size_bytes")
        digest = reference.get("sha256")
        if (
            relative.is_absolute()
            or relative.parts[: len(_ALLOWED_ROOT.parts)] != _ALLOWED_ROOT.parts
            or any(part in ("", ".", "..") for part in relative.parts)
            or "\\" in str(reference.get("path", ""))
            or isinstance(size, bool)
            or not isinstance(size, int)
            or size < 1
            or size > MAX_RASTER_BYTES
            or not isinstance(digest, str)
            or not _SHA256.fullmatch(digest)
        ):
            raise ScenarioAssetsUnavailable("Scenario raster reference is outside the allowed set.")

        try:
            root = self.assets.project_root.resolve(strict=True)
            target = (root / Path(*relative.parts)).resolve(strict=True)
            if not target.is_relative_to(root) or not target.is_file():
                raise ScenarioAssetsUnavailable("Scenario raster asset is unavailable.")
            with target.open("rb") as stream:
                payload = stream.read(MAX_RASTER_BYTES + 1)
        except ScenarioAssetsUnavailable:
            raise
        except OSError as exc:
            raise ScenarioAssetsUnavailable("Scenario raster asset is unavailable.") from exc
        if len(payload) != size or len(payload) > MAX_RASTER_BYTES:
            raise ScenarioAssetsUnavailable("Scenario raster size changed.")
        if hashlib.sha256(payload).hexdigest() != digest:
            raise ScenarioAssetsUnavailable("Scenario raster failed integrity verification.")
        _validate_tiff_metadata(payload, reference)
        return payload, reference


def _validate_tiff_metadata(payload: bytes, reference: dict[str, Any]) -> None:
    """Validate the original TIFF against its manifest record without rewriting it."""
    try:
        with MemoryFile(payload) as memory_file, memory_file.open() as dataset:
            grid = reference["grid"]
            nodata_value = reference["nodata_value"]
            if (
                dataset.driver != "GTiff"
                or dataset.count != 1
                or dataset.dtypes != ("float32",)
                or dataset.width != grid["width"]
                or dataset.height != grid["height"]
                or dataset.crs is None
                or dataset.crs.to_string() != grid["crs"]
                or list(dataset.transform.to_gdal())
                != [
                    grid["affine_transform"][2],
                    grid["affine_transform"][0],
                    grid["affine_transform"][1],
                    grid["affine_transform"][5],
                    grid["affine_transform"][3],
                    grid["affine_transform"][4],
                ]
                or dataset.nodata != nodata_value
            ):
                raise ValueError("TIFF grid or band metadata differs from manifest")
            values = dataset.read(1, masked=True)
            nodata_count = int(values.mask.sum())
            if (
                nodata_count != reference["nodata_cell_count"]
                or int(values.count()) != reference["valid_cell_count"]
                or dataset.tags().get("NODATA") != reference["nodata_meaning"]
                or dataset.tags().get("STATUS") != reference["source_status_tag"]
                or dataset.units != (None,)
                or reference.get("band_units_metadata") is not None
            ):
                raise ValueError("TIFF mask or provenance metadata differs from manifest")
    except Exception as exc:
        raise ScenarioAssetsUnavailable("Scenario TIFF metadata failed validation.") from exc


def _validate_saved_timestamp(value: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 20
        or not value.endswith("Z")
        or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value)
    ):
        raise InvalidScenarioSelector("valid_time_utc must be a canonical UTC instant.")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise InvalidScenarioSelector("valid_time_utc is invalid.") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise InvalidScenarioSelector("valid_time_utc must be UTC.")
