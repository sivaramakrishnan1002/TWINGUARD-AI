"""Read-only inventory of named OSM waterways intersecting the buffered CMA."""
from __future__ import annotations

from collections import defaultdict, deque
from pathlib import Path

import osmium
from pyproj import Transformer
from shapely.geometry import LineString, box
from shapely.ops import transform

ROOT = Path(__file__).resolve().parents[1]
PBF = ROOT / "data/raw/roads/southern-zone-latest.osm.pbf"
OUT = ROOT / "docs/OSM_WATERWAYS.md"
BOUNDS = (79.984, 12.833, 80.365, 13.311)
TARGETS = {
    "adyar", "adyar river", "cooum", "cooum river", "kosasthalaiyar",
    "kosasthalaiyar river", "buckingham canal", "otteri nala",
}


class Inventory(osmium.SimpleHandler):
    def __init__(self) -> None:
        super().__init__()
        self.clip = box(*BOUNDS)
        self.project = Transformer.from_crs("EPSG:4326", "EPSG:32644", always_xy=True).transform
        self.rows: list[dict] = []
        self.errors = 0

    def way(self, way) -> None:
        tags = dict(way.tags)
        water_feature = "waterway" in tags or tags.get("natural") == "water" or "water" in tags
        if not water_feature:
            return
        names = [(key, tags.get(key, "")) for key in ("name", "name:en", "alt_name") if tags.get(key)]
        if not names:
            return
        try:
            coords = [(node.location.lon, node.location.lat) for node in way.nodes if node.location.valid()]
            if len(coords) < 2:
                return
            line = LineString(coords)
            clipped = line.intersection(self.clip)
            if clipped.is_empty:
                return
            length_km = transform(self.project, clipped).length / 1000.0
            if length_km <= 0:
                return
            exact = [(key, value) for key, value in names if value.strip().casefold() in TARGETS]
            self.rows.append({
                "id": way.id,
                "nodes": (way.nodes[0].ref, way.nodes[-1].ref),
                "names": names,
                "exact": exact,
                "tags": tags,
                "km": length_km,
            })
        except Exception:
            self.errors += 1


def connected_components(rows: list[dict]) -> tuple[int, int]:
    if not rows:
        return 0, 0
    by_node: dict[int, list[int]] = defaultdict(list)
    for i, row in enumerate(rows):
        for node in set(row["nodes"]):
            by_node[node].append(i)
    adj: dict[int, set[int]] = defaultdict(set)
    for indexes in by_node.values():
        for a in indexes:
            adj[a].update(i for i in indexes if i != a)
    unseen = set(range(len(rows)))
    components = 0
    while unseen:
        components += 1
        todo = [unseen.pop()]
        while todo:
            for nxt in adj[todo.pop()] & unseen:
                unseen.remove(nxt)
                todo.append(nxt)
    degree_one = sum(1 for indexes in by_node.values() if len(indexes) == 1)
    return components, degree_one


def main() -> None:
    parser = Inventory()
    parser.apply_file(str(PBF), locations=True, idx="sparse_mem_map")

    targets: dict[str, list[dict]] = {name: [] for name in sorted(TARGETS)}
    other: dict[str, float] = defaultdict(float)
    other_ids: dict[str, list[int]] = defaultdict(list)
    exact_rows: list[dict] = []
    for row in parser.rows:
        if row["exact"]:
            exact_rows.append(row)
            for _, value in row["exact"]:
                targets[value.strip().casefold()].append(row)
        for key in {value.strip() for _, value in row["names"]}:
            if key and key.casefold() not in TARGETS:
                other[key] += row["km"]
                other_ids[key].append(row["id"])
    others = sorted(((name, km) for name, km in other.items() if km > 2.0), key=lambda x: -x[1])

    lines = [
        "# Named OSM waterways in the buffered CMA bounds",
        "",
        "Read-only parse of `data/raw/roads/southern-zone-latest.osm.pbf` with pyosmium. Bounds are W 79.984, S 12.833, E 80.365, N 13.311. Candidate features are ways with a `waterway` tag, `natural=water`, or a `water` tag. Names match only when the complete `name`, `name:en`, or `alt_name` field, after trimming and case-folding, equals a requested name; semicolon-separated values are not split. Way geometries are clipped to the bounds and lengths measured after projection to EPSG:32644. Water-area ways are represented by their OSM way geometry boundary; this is a length inventory, not polygon area.",
        "",
        "## Requested names",
        "",
        "| Requested name | Found? | Way IDs | Total clipped length (km) | Name field and water tags |",
        "|---|---|---|---:|---|",
    ]
    for target in sorted(TARGETS):
        rows = targets[target]
        ids = sorted({row["id"] for row in rows})
        km = sum(row["km"] for row in {r["id"]: r for r in rows}.values())
        used = sorted({f"{key}={value.strip()}" for row in rows for key, value in row["exact"]})
        tagsets = sorted({", ".join(f"{k}={v}" for k, v in sorted(row["tags"].items())) for row in rows})
        fields = "; ".join(used + ["tags: " + ts for ts in tagsets]) or "—"
        idtext = ", ".join(map(str, ids)) or "—"
        lines.append(f"| {target.title()} | {'yes' if rows else 'no'} | {idtext} | {km:.3f} | {fields} |")

    components, degree_one = connected_components(exact_rows)
    lines.extend(["", "## Other named water features over 2 km", "", "| OSM name value | Total clipped length (km) | Way IDs |", "|---|---:|---|"])
    for name, km in others:
        ids = sorted(set(other_ids[name]))
        lines.append(f"| {name.replace('|', '\\|')} | {km:.3f} | {', '.join(map(str, ids))} |")
    lines.extend([
        "",
        "## Connectivity and limits",
        "",
        f"The requested-name ways form {components} connected component(s) by shared OSM endpoint node IDs, with {degree_one} degree-one endpoints. This endpoint-only check means the requested named features look **fragmented** in the named subset; unnamed connector ways are not included, so it does not prove that the underlying water network is physically disconnected. A complete network cannot be established from names alone. The PBF may omit or simplify features, and intersections at way interiors are not treated as connected unless represented by a shared endpoint node.",
        f"",
        f"Ways with unavailable/invalid node geometry skipped due parsing errors: {parser.errors}.",
    ])
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}; parsed named water ways={len(parser.rows)}, errors={parser.errors}")


if __name__ == "__main__":
    main()
