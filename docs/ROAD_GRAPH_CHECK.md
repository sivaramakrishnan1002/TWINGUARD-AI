# Road graph sanity check

Read-only diagnosis of the existing graph and facility layers. The output JSON is a new file; no existing features were changed.

## Connectivity

| Metric | Result |
|---|---:|
| Nodes | 508,854 |
| Directed arcs | 1,071,656 |
| Weakly connected components | 192 |
| Strongly connected components | 740 |
| Largest weak component | 506,471 nodes (99.53%) |
| Largest SCC | 505,042 nodes (99.25%) |
| Largest SCC directed arcs | 99.37% |
| Road length with both segment endpoints inside largest SCC | 18,742.9 km / 18,849.6 km (99.43%) |
| Directed arc length retained inside largest SCC | 35,345.4 km-equivalent / 35,524.3 (99.50%) |
| Degree-1 dead-end nodes | 51,124 |

The saved graph has no separately recorded dropped-component table. The table below lists every weak component outside the largest, as isolated components in the saved topology; the exact cause is not inferable from the saved layers alone. This diagnostic did not drop nodes or edges.

| Component ID | Nodes | Directed arcs | Reason/status |
|---:|---:|---:|---|
| 0 | 9 | 16 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 1 | 14 | 26 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 2 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 3 | 4 | 8 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 4 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 5 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 6 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 7 | 4 | 6 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 8 | 4 | 6 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 9 | 6 | 10 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 10 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 11 | 4 | 6 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 12 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 13 | 6 | 10 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 14 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 15 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 16 | 3 | 4 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 17 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 18 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 19 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 20 | 3 | 4 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 21 | 65 | 136 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 22 | 6 | 10 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 23 | 49 | 96 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 24 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 25 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 26 | 6 | 10 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 27 | 4 | 6 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 28 | 4 | 6 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 29 | 5 | 8 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 30 | 4 | 6 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 31 | 7 | 12 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 32 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 33 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 34 | 3 | 4 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 35 | 4 | 6 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 36 | 4 | 6 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 37 | 16 | 30 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 38 | 3 | 4 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 39 | 4 | 6 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 40 | 16 | 32 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 41 | 4 | 8 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 42 | 18 | 34 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 44 | 5 | 8 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 45 | 3 | 4 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 46 | 4 | 8 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 47 | 11 | 20 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 48 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 49 | 3 | 4 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 50 | 5 | 8 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 51 | 18 | 34 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 52 | 4 | 6 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 53 | 7 | 12 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 54 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 55 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 56 | 14 | 26 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 57 | 5 | 8 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 58 | 16 | 40 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 59 | 4 | 8 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 60 | 6 | 14 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 61 | 3 | 4 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 62 | 5 | 8 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 63 | 4 | 8 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 64 | 5 | 10 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 65 | 50 | 102 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 66 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 67 | 43 | 90 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 68 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 69 | 5 | 8 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 70 | 3 | 4 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 71 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 72 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 73 | 18 | 40 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 74 | 4 | 6 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 75 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 76 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 77 | 10 | 18 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 78 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 79 | 14 | 26 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 80 | 532 | 1114 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 81 | 16 | 30 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 82 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 83 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 84 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 85 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 86 | 96 | 202 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 87 | 11 | 22 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 88 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 89 | 7 | 12 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 90 | 20 | 38 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 91 | 16 | 30 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 92 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 93 | 26 | 54 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 94 | 12 | 26 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 95 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 96 | 37 | 65 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 97 | 7 | 12 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 98 | 24 | 52 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 99 | 309 | 666 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 100 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 101 | 26 | 52 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 102 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 103 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 104 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 105 | 22 | 54 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 106 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 107 | 4 | 6 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 108 | 5 | 8 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 109 | 13 | 24 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 110 | 19 | 40 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 111 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 112 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 113 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 114 | 18 | 31 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 115 | 4 | 6 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 116 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 117 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 118 | 3 | 4 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 119 | 7 | 14 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 120 | 24 | 46 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 121 | 9 | 16 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 122 | 4 | 6 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 123 | 10 | 18 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 124 | 9 | 16 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 125 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 126 | 9 | 24 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 127 | 4 | 6 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 128 | 6 | 10 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 129 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 130 | 9 | 16 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 131 | 35 | 68 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 132 | 12 | 22 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 133 | 3 | 4 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 134 | 14 | 28 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 135 | 9 | 16 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 136 | 10 | 18 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 137 | 6 | 10 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 138 | 10 | 18 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 139 | 3 | 4 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 140 | 7 | 12 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 141 | 7 | 12 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 142 | 27 | 52 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 143 | 25 | 48 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 144 | 9 | 16 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 145 | 7 | 12 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 146 | 4 | 6 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 147 | 3 | 4 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 148 | 5 | 8 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 149 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 150 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 151 | 3 | 4 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 152 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 153 | 3 | 4 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 154 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 155 | 3 | 4 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 156 | 6 | 10 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 157 | 35 | 68 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 158 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 159 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 160 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 161 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 162 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 163 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 164 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 165 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 166 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 167 | 7 | 12 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 168 | 6 | 10 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 169 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 170 | 7 | 14 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 171 | 6 | 12 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 172 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 173 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 174 | 4 | 6 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 175 | 60 | 142 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 176 | 4 | 6 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 177 | 10 | 18 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 178 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 179 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 180 | 3 | 4 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 181 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 182 | 3 | 4 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 183 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 184 | 3 | 4 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 185 | 3 | 4 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 186 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 187 | 2 | 2 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 188 | 4 | 6 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 189 | 8 | 14 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 190 | 4 | 6 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |
| 191 | 7 | 12 | Separate saved endpoint component; likely isolated/clipped/disconnected source data, exact cause unverified |

## Highway classes

The extractor accepted these OSM `highway` values: `bridleway`, `cycleway`, `footway`, `living_street`, `motorway`, `motorway_link`, `path`, `pedestrian`, `primary`, `primary_link`, `residential`, `road`, `secondary`, `secondary_link`, `service`, `steps`, `tertiary`, `tertiary_link`, `track`, `trunk`, `trunk_link`, `unclassified`. Present in the saved segment layer (counts are segments): `cycleway` 242, `footway` 6,124, `living_street` 8,031, `motorway` 2,081, `motorway_link` 592, `path` 7,518, `pedestrian` 658, `primary` 22,748, `primary_link` 2,184, `residential` 346,506, `road` 17, `secondary` 13,787, `secondary_link` 324, `service` 82,608, `steps` 398, `tertiary` 39,748, `tertiary_link` 254, `track` 12,679, `trunk` 3,348, `trunk_link` 1,191, `unclassified` 15,269. `bridleway` was accepted by code but has no saved segment. Other highway values and missing highway tags were excluded by the extraction filter.

## Facilities

Every listed facility point was assigned to its nearest saved road node to compute a diagnostic distance; this is not a validated turn-access snap rule. The 500 m count uses straight-line distance to the nearest road node. Segment distances use the existing `nearest_road_distance_m` field.

| Category | OSM facility points | Assigned nearest node | Within 500 m node | Node distance median / p95 / max (m) | Road segment distance median / p95 (m) |
|---|---:|---:|---:|---|---|
| hospital | 848 | 848 | 848 | 23.0 / 50.7 / 114.0 | 14.5 / 32.1 |
| clinic | 587 | 587 | 587 | 20.6 / 50.4 / 92.6 | 12.2 / 23.9 |
| school | 696 | 696 | 696 | 33.5 / 73.9 / 131.6 | 25.3 / 67.6 |
| college | 188 | 188 | 188 | 35.5 / 84.4 / 143.5 | 25.1 / 80.2 |
| shelter | 171 | 171 | 171 | 10.1 / 64.3 / 136.6 | 5.5 / 58.2 |
| fire_station | 15 | 15 | 15 | 25.2 / 40.2 / 44.3 | 20.9 / 33.0 |
| police | 121 | 121 | 121 | 19.6 / 39.0 / 48.7 | 12.6 / 30.6 |

The source inventory reports 908 hospitals, 706 schools and 172 shelters, compared with 848, 696 and 171 in this facility layer. The inventory uses a rectangular bounding box; the extracted layer covers the CMA polygon plus 2 km, and geometry conversion, tag grouping and deduplication may also differ. These are plausible scope/method causes, but the exact 60/10/1 differences remain unresolved without a like-for-like recount of the PBF using the same geometry, tags and deduplication rules. [repo: `docs/OSM_COUNTS.md`, saved `facilities` layer]

For a strict CMA-only subset, the database's `in_cma` flag (migration 011, geometry intersects the selected boundary in EPSG:32644) yields 830 hospitals, 571 clinics, 685 schools, 175 colleges, 167 shelters, 15 fire stations and 118 police facilities. These counts exclude buffered points outside the CMA; all rows remain stored. The complete category list is in `docs/CMA_FACILITY_COUNTS.csv`.

## Example routes

Sample hospital-to-shelter routes use nearest-node attachments and Dijkstra over saved directed arcs weighted by segment lengths. This only tests graph connectivity; it does not check closures, bridge capacity, flood depth, access restrictions, or safety.

| Hospital | Shelter | Straight distance (m) | Directed network path (m) | Routable? |
|---|---|---:|---:|---|
| Tamil Nadu Government Dental College & Hospital, Chennai | unnamed | 273 | 389 | yes |
| unnamed | unnamed | 282 | 424 | yes |
| The Arya Vysya Meternity Home and Child Welfare Centre | unnamed | 441 | 1234 | yes |

## 100 m population proximity

The existing all-road buffer contains an estimated 6,072,870.5 of 6,203,811.3 population-grid total (97.89%). The buffer includes footpaths, service roads, steps, tracks and other minor classes, so the high coverage is not evidence that 98% of residents have a usable evacuation route. The individual contribution of minor classes was not recomputed in this fix-up. [repo: existing road-buffer population summary]

## Limitations

The source graph is a static OSM snapshot. The SCC is a strict directed reachability measure and can be small where one-way links or disconnected access roads exist. Nearest-node assignment uses no maximum snap distance; counts within 500 m show how often nearest nodes are close, not that each facility is actually connected to a usable entrance. No graph edges were removed during this check.
