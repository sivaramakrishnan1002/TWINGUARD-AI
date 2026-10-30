"""Bounded, read-only projections of A20's checked-in scenario manifest."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


MAX_MANIFEST_BYTES = 256 * 1024
MAX_RASTER_REFERENCES = 64
MAX_RASTER_BYTES = 64 * 1024
MAX_TOTAL_RASTER_BYTES = 1024 * 1024
_SCENARIO_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_CATALOG_KEYS = (
    "schema_version",
    "artifact_version",
    "status",
    "grid",
    "depth_units",
    "nodata",
    "provenance",
    "context_layers",
    "limitations",
    "presentation_policy",
    "time_basis",
)
_SERIES_SUMMARY_KEYS = (
    "event_id",
    "scenario_id",
    "source_mode",
    "window_start_utc",
    "window_end_utc_inclusive",
    "member_count",
    "rainfall_semantics",
    "band_semantics",
)


class ScenarioAssetsUnavailable(RuntimeError):
    """Manifest or referenced assets are missing, invalid, or changed."""


class ScenarioAssetNotFound(LookupError):
    """No exact manifest identity matches the requested event and scenario."""


class InvalidScenarioSelector(ValueError):
    """Selector values do not satisfy the bounded C9 path shape."""


class ScenarioAssetRepository:
    """Read manifest metadata after verifying a bounded set of raster refs.

    The public operations return JSON-compatible metadata and never raster
    bytes. All paths in the manifest are resolved under ``project_root``;
    symlinks that escape that root and oversized content fail closed.
    """

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = (project_root or Path(__file__).resolve().parents[4]).resolve()
        self.manifest_path = self.project_root / "data/features/visualization3d/batch2_v1/manifest.json"

    def catalog(self) -> dict[str, Any]:
        manifest = self._validated_manifest()
        catalog = {key: manifest[key] for key in _CATALOG_KEYS}
        catalog["scenario_series"] = []
        for series in manifest["scenario_series"]:
            summary = {key: series[key] for key in _SERIES_SUMMARY_KEYS}
            summary["saved_times_utc"] = [item["valid_time_utc"] for item in series["slices"]]
            catalog["scenario_series"].append(summary)
        return catalog

    def asset(self, event_id: str, scenario_id: str) -> dict[str, Any]:
        _validate_selector(event_id, scenario_id)
        manifest = self._validated_manifest()
        matches = [
            series
            for series in manifest["scenario_series"]
            if series.get("event_id") == event_id and series.get("scenario_id") == scenario_id
        ]
        if not matches:
            raise ScenarioAssetNotFound("No exact saved scenario asset was found.")
        if len(matches) != 1:
            raise ScenarioAssetsUnavailable("Scenario manifest contains an ambiguous identity.")
        return {
            **{key: manifest[key] for key in _CATALOG_KEYS if key != "context_layers"},
            "series": matches[0],
        }

    def _validated_manifest(self) -> dict[str, Any]:
        try:
            root = self.project_root.resolve(strict=True)
            manifest_path = self.manifest_path.resolve(strict=True)
            if not manifest_path.is_relative_to(root) or not manifest_path.is_file():
                raise ScenarioAssetsUnavailable("Scenario manifest is unavailable.")
            manifest_size = manifest_path.stat().st_size
            if manifest_size <= 0 or manifest_size > MAX_MANIFEST_BYTES:
                raise ScenarioAssetsUnavailable("Scenario manifest exceeds the allowed size.")
            with manifest_path.open("rb") as stream:
                raw = stream.read(MAX_MANIFEST_BYTES + 1)
            if len(raw) != manifest_size or len(raw) > MAX_MANIFEST_BYTES:
                raise ScenarioAssetsUnavailable("Scenario manifest changed during read.")
            manifest = json.loads(raw)
            self._validate_manifest_shape(manifest)
            self._verify_raster_references(root, manifest)
            return manifest
        except ScenarioAssetsUnavailable:
            raise
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            # Do not expose local paths or low-level filesystem diagnostics.
            raise ScenarioAssetsUnavailable("Scenario manifest or assets failed validation.") from exc

    @staticmethod
    def _validate_manifest_shape(manifest: Any) -> None:
        if not isinstance(manifest, dict):
            raise ScenarioAssetsUnavailable("Scenario manifest is invalid.")
        if (
            manifest.get("schema_version") != "1.0.0"
            or manifest.get("artifact_version") != "batch2_v1"
            or manifest.get("status") != "DERIVED_ASSUMPTION_BASED_RESEARCH_SCENARIO"
        ):
            raise ScenarioAssetsUnavailable("Unsupported scenario manifest version.")
        series = manifest.get("scenario_series")
        context = manifest.get("context_layers")
        if not isinstance(series, list) or len(series) != 3 or not isinstance(context, list) or len(context) != 4:
            raise ScenarioAssetsUnavailable("Scenario manifest exceeds record limits.")
        identities: set[tuple[str, str]] = set()
        for item in series:
            if not isinstance(item, dict):
                raise ScenarioAssetsUnavailable("Scenario series record is invalid.")
            _validate_selector(item.get("event_id"), item.get("scenario_id"))
            identity = (item["event_id"], item["scenario_id"])
            if identity in identities:
                raise ScenarioAssetsUnavailable("Scenario manifest identity is duplicated.")
            identities.add(identity)
            _validate_timestamp(item.get("window_start_utc"))
            _validate_timestamp(item.get("window_end_utc_inclusive"))
            slices = item.get("slices")
            if not isinstance(slices, list) or len(slices) != 5:
                raise ScenarioAssetsUnavailable("Scenario saved-time list is invalid.")
            if not isinstance(item.get("members"), list) or len(item["members"]) != 20:
                raise ScenarioAssetsUnavailable("Scenario parameter-member list is invalid.")
            saved_times: list[str] = []
            for saved in slices:
                if not isinstance(saved, dict):
                    raise ScenarioAssetsUnavailable("Scenario saved-time record is invalid.")
                _validate_timestamp(saved.get("valid_time_utc"))
                saved_times.append(saved["valid_time_utc"])
                if not isinstance(saved.get("bands"), dict) or set(saved["bands"]) != {"p05", "p50", "p95"}:
                    raise ScenarioAssetsUnavailable("Scenario band set is invalid.")
            if saved_times != sorted(set(saved_times)):
                raise ScenarioAssetsUnavailable("Scenario saved times must be unique and ordered.")
        for item in context:
            if not isinstance(item, dict):
                raise ScenarioAssetsUnavailable("Scenario context record is invalid.")
            _validate_timestamp(item.get("window_start_utc"))
            _validate_timestamp(item.get("window_end_utc_inclusive"))
            bands = item.get("bands")
            if not isinstance(bands, dict) or set(bands) != {"mean", "p05", "p95"}:
                raise ScenarioAssetsUnavailable("Scenario context bands are invalid.")
            if item.get("temporal_kind") == "per_cell_event_peak":
                if item.get("valid_time_utc") is not None or item.get("selected_hour_index_zero_based") is not None:
                    raise ScenarioAssetsUnavailable("Per-cell event peak must not claim one valid instant.")
            elif item.get("temporal_kind") == "selected_hour":
                _validate_timestamp(item.get("valid_time_utc"))
                index = item.get("selected_hour_index_zero_based")
                if isinstance(index, bool) or not isinstance(index, int) or index < 0:
                    raise ScenarioAssetsUnavailable("Selected-hour context index is invalid.")
            else:
                raise ScenarioAssetsUnavailable("Unsupported scenario context time semantics.")

    @staticmethod
    def _verify_raster_references(root: Path, manifest: dict[str, Any]) -> None:
        refs: list[dict[str, Any]] = []
        for series in manifest["scenario_series"]:
            if not isinstance(series, dict) or len(series.get("slices", [])) > 5:
                raise ScenarioAssetsUnavailable("Scenario series exceeds record limits.")
            for saved_slice in series.get("slices", []):
                refs.extend(saved_slice.get("bands", {}).values())
        for context in manifest["context_layers"]:
            if not isinstance(context, dict):
                raise ScenarioAssetsUnavailable("Scenario context record is invalid.")
            refs.extend(context.get("bands", {}).values())
        if len(refs) > MAX_RASTER_REFERENCES:
            raise ScenarioAssetsUnavailable("Scenario manifest exceeds raster reference limit.")
        total_bytes = 0
        for ref in refs:
            if not isinstance(ref, dict):
                raise ScenarioAssetsUnavailable("Scenario raster reference is invalid.")
            relative = PurePosixPath(ref.get("path", ""))
            size = ref.get("size_bytes")
            digest = ref.get("sha256")
            if (
                relative.is_absolute()
                or not relative.parts
                or any(part in (".", "..") for part in relative.parts)
                or "\\" in str(ref.get("path", ""))
                or isinstance(size, bool)
                or not isinstance(size, int)
                or size < 1
                or size > MAX_RASTER_BYTES
                or not isinstance(digest, str)
                or not _SHA256.fullmatch(digest)
            ):
                raise ScenarioAssetsUnavailable("Scenario raster reference is invalid.")
            total_bytes += size
            if total_bytes > MAX_TOTAL_RASTER_BYTES:
                raise ScenarioAssetsUnavailable("Scenario assets exceed the total read limit.")
            path = (root / Path(*relative.parts)).resolve(strict=True)
            if not path.is_relative_to(root) or not path.is_file() or path.stat().st_size != size:
                raise ScenarioAssetsUnavailable("Scenario raster asset is unavailable or changed.")
            if _sha256(path, size) != digest:
                raise ScenarioAssetsUnavailable("Scenario raster asset failed integrity verification.")


def _validate_selector(event_id: str, scenario_id: str) -> None:
    if not isinstance(event_id, str) or len(event_id) != 10:
        raise InvalidScenarioSelector("event_id must be an ISO date.")
    try:
        if date.fromisoformat(event_id).isoformat() != event_id:
            raise ValueError
    except ValueError as exc:
        raise InvalidScenarioSelector("event_id must be an ISO date.") from exc
    if not isinstance(scenario_id, str) or not _SCENARIO_ID.fullmatch(scenario_id):
        raise InvalidScenarioSelector("scenario_id has an invalid format.")


def _validate_timestamp(value: Any) -> None:
    if not isinstance(value, str) or not value.endswith("Z") or len(value) > 32:
        raise ScenarioAssetsUnavailable("Scenario timestamp is not an exact UTC instant.")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ScenarioAssetsUnavailable("Scenario timestamp is invalid.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ScenarioAssetsUnavailable("Scenario timestamp is not UTC.")


def _sha256(path: Path, expected_size: int) -> str:
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(64 * 1024), b""):
            total += len(block)
            if total > expected_size:
                raise ScenarioAssetsUnavailable("Scenario raster asset changed during verification.")
            digest.update(block)
    if total != expected_size:
        raise ScenarioAssetsUnavailable("Scenario raster asset changed during verification.")
    return digest.hexdigest()
