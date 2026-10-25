import json
from pathlib import Path


def test_pdf_map_inspection_records_available_geopdfs_and_missing_december_folder():
    root = Path(__file__).resolve().parents[2]
    records = json.loads((root / "docs/PDF_MAP_INSPECTION.json").read_text(encoding="utf-8"))
    by_source = {row["source"]: row for row in records}
    assert by_source["data/raw/historical_floods/2021/ChennaiCity-ChennaiCorporationTaluk-4.pdf"]["geopdf_embedded_georeferencing"] is True
    assert by_source["data/raw/historical_floods/2023/tncyclone50dsc07122023_0600hrs_map.pdf"]["geopdf_embedded_georeferencing"] is True
    assert sum(len(page["embedded_images"]) for page in by_source["data/raw/historical_floods/2021/ChennaiCity-ChennaiCorporationTaluk-4.pdf"]["pages"]) == 6
    assert sum(len(page["embedded_images"]) for page in by_source["data/raw/historical_floods/2023/tncyclone50dsc07122023_0600hrs_map.pdf"]["pages"]) == 24
    assert by_source["data/raw/historical_floods/2015/december_maps"]["status"] == "folder absent; December maps not provided"
