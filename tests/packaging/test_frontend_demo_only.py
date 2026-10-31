"""B29 static guard: the mounted product experience is local fixture-only."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"
PRODUCT_ROOTS = [
    FRONTEND / "src/ui/App.tsx",
    FRONTEND / "src/ui/product",
    FRONTEND / "src/ui/demo",
]
FORBIDDEN = [
    (re.compile(r"\bfetch\s*\(", re.I), "fetch call"),
    (re.compile(r"\baxios\b", re.I), "Axios client"),
    (re.compile(r"\bXMLHttpRequest\b", re.I), "XHR client"),
    (re.compile(r"\bWebSocket\b", re.I), "WebSocket client"),
    (re.compile(r"\bEventSource\b", re.I), "EventSource client"),
    (re.compile(r"(?:scenarioApi|AI_SCENARIO_ORIGIN|B13ReplayView|trackBAdapter|decisionSupportAdapter)", re.I), "service/B18 adapter import"),
    (re.compile(r"https?://|/scenario-visualization|/replay-alerts", re.I), "service endpoint"),
]


def product_sources() -> list[Path]:
    files: list[Path] = []
    for path in PRODUCT_ROOTS:
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(path.rglob("*.ts"))
            files.extend(path.rglob("*.tsx"))
    return sorted(files)


class FrontendDemoOnlyTests(unittest.TestCase):
    def test_b29_source_paths_have_no_network_clients_or_service_adapters(self) -> None:
        sources = product_sources()
        self.assertTrue(sources, "B29 source paths should exist")
        for source in sources:
            text = source.read_text(encoding="utf-8")
            for pattern, label in FORBIDDEN:
                with self.subTest(path=source.relative_to(ROOT), forbidden=label):
                    self.assertIsNone(pattern.search(text), f"{label} found in {source.relative_to(ROOT)}")

    def test_mount_uses_only_product_experience_and_existing_bootstrap(self) -> None:
        app = (FRONTEND / "src/ui/App.tsx").read_text(encoding="utf-8")
        bootstrap = (FRONTEND / "src/main.tsx").read_text(encoding="utf-8")
        self.assertIn("./product/ProductExperience", app)
        for forbidden in ("scenario3d", "scenarioApi", "B13ReplayView", "adapters/trackB", "adapters/decisionSupport"):
            self.assertNotIn(forbidden, app)
        self.assertIn("./ui/App", bootstrap)

    def test_built_static_product_has_demo_sections_and_no_service_origins(self) -> None:
        dist = FRONTEND / "dist"
        assets = list((dist / "assets").glob("index-*.js")) if (dist / "assets").exists() else []
        self.assertTrue(assets, "Run the install-free frontend build before the packaged UI smoke check")
        bundle = "\n".join(asset.read_text(encoding="utf-8") for asset in assets)
        for label in ("Situation Overview", "3D Flood Twin", "Reservoirs & Alerts", "Emergency Response", "What-if lab", "Data & system", "SIMULATED"):
            with self.subTest(label=label):
                self.assertIn(label, bundle)
        for forbidden in ("127.0.0.1:8000", "127.0.0.1:8080", "/scenario-visualization", "/replay-alerts"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, bundle)


if __name__ == "__main__":
    unittest.main()
