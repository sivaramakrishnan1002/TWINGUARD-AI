"""Guard the AI image's pinned Rasterio system-runtime dependency."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = ROOT / "services/ai-service/Dockerfile"


def test_ai_image_installs_libexpat_and_cleans_apt_indexes_in_one_layer() -> None:
    lines = DOCKERFILE.read_text(encoding="utf-8").splitlines()
    run_lines: list[str] = []
    for index, line in enumerate(lines):
        if line.startswith("RUN apt-get update"):
            run_lines = [line]
            while run_lines[-1].rstrip().endswith("\\"):
                index += 1
                run_lines.append(lines[index])
            break

    assert run_lines
    apt_layer = " ".join(line.rstrip().removesuffix("\\").strip() for line in run_lines)
    assert "apt-get update" in apt_layer
    assert "apt-get install -y --no-install-recommends libexpat1" in apt_layer
    assert "rm -rf /var/lib/apt/lists/*" in apt_layer


def test_rasterio_version_remains_pinned() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    assert "rasterio==1.5.2" in dockerfile
