# Named OSM waterways in the buffered CMA bounds

Read-only parse of `data/raw/roads/southern-zone-latest.osm.pbf` with pyosmium. Bounds are W 79.984, S 12.833, E 80.365, N 13.311. Candidate features are ways with a `waterway` tag, `natural=water`, or a `water` tag. Names match only when the complete `name`, `name:en`, or `alt_name` field, after trimming and case-folding, equals a requested name; semicolon-separated values are not split. Way geometries are clipped to the bounds and lengths measured after projection to EPSG:32644. Water-area ways are represented by their OSM way geometry boundary; this is a length inventory, not polygon area.

## Requested names

| Requested name | Found? | Way IDs | Total clipped length (km) | Name field and water tags |
|---|---|---|---:|---|
| Adyar | no | — | 0.000 | — |
| Adyar River | yes | 23110069, 178105896, 178105900, 202471872, 383852846 | 50.130 | name=Adyar River; tags: boat=no, layer=-1, name=Adyar River, tunnel=yes, waterway=river; tags: boat=no, name=Adyar River, name:ml=അടയാർ നദി, name:ta=அடையாறு நதி, waterway=river, wikidata=Q2825422, wikipedia=en:Adyar River; tags: boat=no, name=Adyar River, waterway=river, wikidata=Q2825422; tags: intermittent=no, name=Adyar River, source:geometry=bing;DigitalGlobeStandard, tidal=no, waterway=river, width=10, wikidata=Q2825422; tags: name=Adyar River, waterway=river, wikidata=Q2825422 |
| Buckingham Canal | yes | 731551448, 822593959, 1080352339, 1080352340, 1127503334, 1492152598, 1492152599 | 56.249 | name:en=Buckingham Canal; name=Buckingham Canal; tags: boat=no, layer=-1, name=Buckingham Kaalvaai, name:en=Buckingham Canal, name:ml=ബക്കിംഗ്ഹാം കൈത്തോട്, name:ta=பக்கிங்ஹாம் கால்வாய், name:te=బకింగ్‌హాం కాలువ, tunnel=culvert, waterway=canal, width=15, wikidata=Q3536830, wikipedia=en:Buckingham Canal; tags: boat=no, name=Buckingham Canal, name:en=Buckingham Canal, name:ta=பக்கிங்ஹாம் கால்வாய், name:te=బకింగ్‌హాం కాలువ, waterway=canal, width=15, wikidata=Q3536830, wikipedia=en:Buckingham Canal; tags: boat=no, name=Buckingham Kaalvaai, name:en=Buckingham Canal, name:ml=ബക്കിംഗ്ഹാം കൈത്തോട്, name:ta=பக்கிங்ஹாம் கால்வாய், name:te=బకింగ్‌హాం కాలువ, waterway=canal, width=15, wikidata=Q3536830, wikipedia=en:Buckingham Canal; tags: layer=-1, name=Buckingham Canal, name:en=Buckingham Canal, name:ml=ബക്കിംഗ്ഹാം കനാൽ, name:ta=பக்கிங்ஹாம் கால்வாய், name:te=బకింగ్‌హాం కాలువ, tunnel=culvert, waterway=canal; tags: name=Buckingham Canal, name:en=Buckingham Canal, name:ml=ബക്കിംഗ്ഹാം കനാൽ, name:ta=பக்கிங்ஹாம் கால்வாய், name:te=బకింగ్‌హాం కాలువ, waterway=canal |
| Cooum | yes | 202505379 | 44.059 | name:en=Cooum; tags: name=கூவம் ஆறு, name:en=Cooum, name:kn=ಕೂವಂ, name:ml=കൂവം, name:ta=கூவம், waterway=river |
| Cooum River | no | — | 0.000 | — |
| Kosasthalaiyar | no | — | 0.000 | — |
| Kosasthalaiyar River | yes | 25395844, 30777996, 910151265, 910151277 | 38.708 | name=Kosasthalaiyar River; tags: name=Kosasthalaiyar River, source=village people, waterway=river, wikidata=Q6433004, wikipedia=en:Kosasthalaiyar River; tags: name=Kosasthalaiyar River, waterway=river, wikidata=Q6433004, wikipedia=en:Kosasthalaiyar River |
| Otteri Nala | no | — | 0.000 | — |

## Other named water features over 2 km

| OSM name value | Total clipped length (km) | Way IDs |
|---|---:|---|
| கூவம் ஆறு | 44.059 | 202505379 |
| Chembarambakkam Lake | 30.164 | 25453624 |
| Buckingham Kaalvaai | 28.231 | 731551448, 1492152598, 1492152599 |
| Puzhal Lake | 27.713 | 25394157 |
| Krishna Canal | 26.869 | 25395366, 384222225, 1547615934, 1547615935 |
| Kortallaiyar River | 16.661 | 133599488 |
| Sholavaram Lake | 14.073 | 25394523 |
| Thiruninravur Lake | 10.369 | 25468747 |
| Otteri Nullah | 10.333 | 27708880 |
| Nemam Lake | 9.959 | 31252968 |
| Joins with Chembarampakkam Surplus | 9.163 | 26188336 |
| Korattur Lake | 8.519 | 25474612 |
| Chembarambakkam irrigation canal | 8.436 | 30137291, 383742981, 836320367, 836320368, 836320369, 836320370, 837068335, 837068336, 1151035773, 1151035774, 1151035775, 1151035776, 1151035777, 1151035778, 1151035779, 1151035780 |
| Red Hills Reservoir Overflow | 8.320 | 31019920, 102550193 |
| Thanthi Channel | 8.277 | 290653341, 383838974, 837068307, 837068308, 1301947363, 1301947366, 1301947367, 1301947374, 1301947375, 1301947378 |
| Arani | 8.145 | 138337576 |
| Retteri Lake | 8.056 | 25474749, 26800736 |
| Ambattur Lake | 7.255 | 25391800, 102459233 |
| Virugambakkam Canal | 7.192 | 102550226, 217802635, 1281940340, 1284526464, 1284526465, 1298345127, 1298345128, 1298345129, 1298345130, 1298345131, 1298345132, 1298345133, 1298345134 |
| Chembrampakkam Surplus to Adayar | 6.059 | 30128515 |
| Mambalam Canal | 5.806 | 23161547, 214162276, 1267739072, 1267739073, 1272450537, 1272450538, 1272450539, 1272450540 |
| Pakkam Lake | 5.590 | 138337748 |
| ETPS Flyash Pond | 5.577 | 30738635, 30738642 |
| Somangalam Lake | 5.307 | 25921389 |
| Ayanambakkam Lake | 5.239 | 1237456198 |
| Chembarampakkam water for irrigation | 5.161 | 290654695, 383754559, 706900387, 706900388, 836326671, 836326672, 836326673, 836326674, 836333668, 836333669, 1151629365, 1151629366, 1453896696, 1453896697 |
| Kovilpadagai Lake | 4.912 | 30078793 |
| Palavedu Lake | 4.893 | 32017928 |
| Perumbakkam Lake | 4.836 | 30424450, 98357524 |
| Banaveduthottam Lake | 4.595 | 95639903 |
| Surplus water drain | 4.522 | 102657796, 833840450, 833840451, 1065781836, 1065781837 |
| Velachery Lake | 4.521 | 25504265, 30606822 |
| Periyathoppu Lake | 4.480 | 29246065, 31020934 |
| Veerangal Canal | 4.438 | 328358961, 1080320415, 1080320416, 1080320417, 1080320418, 1232632860, 1232632861 |
| ADHANUR LAKE | 4.210 | 102303002 |
| Pattabiram lake | 4.007 | 138307641 |
| Padappai Lake | 3.882 | 30778453 |
| Poonamallee Lake | 3.780 | 1236160012 |
| NALLUR ERIKARAII | 3.640 | 462909812 |
| Tiruneermalai Eri | 3.613 | 23648233 |
| Thiruneermalai Lake | 3.613 | 23648233 |
| Manivakkam Lake | 3.279 | 32066592 |
| Mittanamalli Lake | 3.169 | 34483989 |
| Kadapakkam Tank | 3.076 | 98315669 |
| Sembakkam lake | 3.072 | 26433707 |
| Nanmangalam Lake | 3.059 | 28260431 |
| Ainsley Canal | 3.024 | 346285748, 1188575627, 1188575628, 1188575631, 1188575632, 1188575635, 1188575636 |
| Captain Cotton Canal | 2.992 | 25474535 |
| Selaiyur Lake | 2.947 | 28260577 |
| Thandurai Lake | 2.902 | 95639930 |
| Mambakkam Lake | 2.777 | 82883544 |
| Ayapakkam Lake | 2.726 | 34618168 |
| Adyar Creek | 2.599 | 111749073 |
| Vellanur Lake | 2.594 | 34484008 |
| Okkiyam Maduvu | 2.572 | 201560881 |
| Kodungaiyur Canal | 2.565 | 25474766 |
| Naattu Kaalvaai | 2.485 | 30118691 |
| Navalur Eri | 2.464 | 30799618 |
| Sathankadu Lake | 2.463 | 661094631 |
| Vandalur Lake | 2.445 | 132192377 |
| Maambakkam Lake | 2.425 | 82883553 |
| Balaji Nagar Lake | 2.390 | 28261148 |
| Porur Lake | 2.360 | 23633592 |
| Vellacheri Lake | 2.326 | 1159363407 |
| Pallikkaranai Anai Tank | 2.325 | 203215028 |
| Madipakkam Lake | 2.269 | 25725027 |
| Karthikeyapuram Lake | 2.269 | 25725027 |
| North River | 2.262 | 22658645, 85130862, 85130915 |
| Vadakkapattu Lake | 2.209 | 28260258 |
| Vengadamangalam, IRPC Lake | 2.190 | 98357449 |
| Kollappancheri Lake | 2.184 | 1236160014 |
| Araabath Lake | 2.155 | 138307626 |
| Pallikkaranai Eri | 2.098 | 203215030 |
| Kolladi Lake | 2.063 | 102459218 |
| Parivakkam Lake | 2.045 | 1236160018 |

## Connectivity and limits

The requested-name ways form 6 connected component(s) by shared OSM endpoint node IDs, with 12 degree-one endpoints. This endpoint-only check means the requested named features look **fragmented** in the named subset; unnamed connector ways are not included, so it does not prove that the underlying water network is physically disconnected. A complete network cannot be established from names alone. The PBF may omit or simplify features, and intersections at way interiors are not treated as connected unless represented by a shared endpoint node.

Ways with unavailable/invalid node geometry skipped due parsing errors: 0.
