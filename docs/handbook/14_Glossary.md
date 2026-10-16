# Glossary

Terms are defined here in plain language. A term’s mention does not mean its feature is already implemented. [repo: `docs/FEATURE_DICTIONARY.md`; user]

| Term | Plain-English meaning |
|---|---|
| AI / machine learning | Computer methods that learn patterns from examples. |
| Alpha product | An early or provisional data release that may still have known limits. |
| API | A defined way for software systems to request information or actions from one another. |
| Bias | The average signed difference between two measurements; the sign convention must be stated. |
| CAG | Comptroller and Auditor General of India, the public audit institution. |
| Calibration | Whether stated probabilities match how often events actually happen. |
| CMA | Chennai Metropolitan Area. This project uses the older boundary provisionally. |
| COG | Cloud Optimized GeoTIFF: a GeoTIFF arranged for efficient partial/cloud access. |
| Counterfactual | A “what if” scenario that changes one condition, such as a closed bridge. |
| CRS | Coordinate Reference System: how map coordinates relate to positions on Earth. |
| Cusec | Cubic foot per second, a flow-rate unit. |
| DEM / DSM | Digital Elevation Model / Digital Surface Model. A DSM includes visible surfaces such as buildings and trees; a bare-earth DEM aims to represent ground. |
| Digital Twin | A digital representation of a real place that is connected to data and can be updated or used to test scenarios. |
| Directed graph | A network whose links can have direction, such as a one-way road. |
| EPSG:32644 | WGS 84 / UTM zone 44N, a projected coordinate system used for Chennai-area metre-based analysis. |
| ERA5 | A global weather reanalysis product; it combines observations and weather modelling and is not a local rain gauge. |
| F1 score | A combined precision/recall score for classification. |
| False alarm | A warning counted as positive when the defined flood outcome did not occur. It cannot be measured without defined outcome labels. |
| Flow accumulation | A terrain-derived count of cells routed toward a cell under a chosen flow model. |
| GFD | Global Flood Database, a MODIS-based flood-event dataset; this project’s event is coarse and regional. |
| GeoJSON / GeoPackage | File formats for vector map features; GeoPackage can store several layers in one file. |
| Georeferencing | Connecting positions in an image/map to real-world coordinates using control points or known map geometry. |
| GRD-HD | ASF Sentinel-1 Ground Range Detected High Definition product label used for the downloaded product family. |
| Hypothesis | A testable statement to compare with evidence. |
| IoU | Intersection over Union: overlap between a predicted and reference map divided by their combined area. |
| mcft | Million cubic feet, a reservoir storage-volume unit. |
| MODIS | Satellite instrument used by the Global Flood Database’s broad flood-event layer. |
| Multimodal | Using more than one kind of input, such as weather, satellite images and terrain. |
| NDEM | National Database for Emergency Management, the NRSC disaster-information source named in project records. |
| NoData | A cell for which the raster provides no usable value. It is different from a valid zero. |
| Nowcasting | A very short-term estimate of current or near-future conditions. |
| ODbL | Open Database Licence, the licence associated with OpenStreetMap data. |
| OpenStreetMap (OSM) | A collaboratively maintained map database; mapping coverage and tags vary by place. |
| Pixel-centre inclusion | A rule that counts a raster cell if its centre falls inside a boundary. |
| PostGIS | A PostgreSQL extension that stores and queries spatial data. |
| Raster | A grid of cells/pixels, each holding one or more values. |
| Relative orbit | The repeating satellite path used to compare acquisitions made from a similar viewing geometry. |
| Reanalysis | A historical weather estimate combining observations with a consistent model. |
| RISAT-1A | Indian radar imaging satellite referenced in the project’s Michaung map context. |
| SAR | Synthetic Aperture Radar: radar imaging that can observe through clouds and at night, but may confuse water with urban surfaces or wet ground. |
| Sentinel-1 | European radar satellite mission; downloaded scenes are not yet processed here. |
| SHA-256 | A checksum that gives a long fingerprint for checking whether a file changed. |
| Strongly connected component | In a directed graph, a group where every node can reach every other by following allowed directions. |
| TWI | Topographic Wetness Index, an estimate based on terrain and flow; this project has only an unvalidated D8 proxy. |
| UTM | Universal Transverse Mercator, a map projection divided into regional zones. |
| Uncertainty | The range of plausible values or outcomes, rather than one certain answer. |
| UNOSAT | United Nations Satellite Centre, provider of the 2015 flood map archive used here. |
| Vector | Map features represented as points, lines or polygons rather than grid cells. |
| WorldCover | ESA land-cover classification product; the project uses the 2021 epoch. |
| WorldPop | Gridded population estimate; the project uses an alpha constrained 2021 product. |
| mcft / cusec | Storage and flow units; they measure different things and cannot be substituted for one another. |
