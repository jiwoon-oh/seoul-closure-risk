# Data

The raw tables are not in this repository. They are public Seoul Open Data tables and are git-ignored, so download them and place them in `data/raw/` (the notebooks read `RAW` from `config.py`).

Provider: Seoul Credit Guarantee Foundation, published on the [Seoul Open Data Plaza](https://data.seoul.go.kr) as the "Seoul Commercial Area Analysis Service" tables. License shown on each dataset page: Korea Open Government License Type 1 (attribution; commercial use and modification allowed). Please check each page for the current terms before reuse.

| Table (English translation of the dataset title) | Dataset page | Used for |
|---|---|---|
| Store counts by commercial area | [OA-15577](https://data.seoul.go.kr/dataList/OA-15577/S/1/datasetView.do) | store counts, openings, closures, franchise stores |
| Estimated sales by commercial area | [OA-15572](https://data.seoul.go.kr/dataList/OA-15572/S/1/datasetView.do) | supporting sales variables |
| Commercial-area boundaries | [OA-15560](https://data.seoul.go.kr/dataList/OA-15560/S/1/datasetView.do) | area type, district, coordinates, area size |
| Street-level pedestrian traffic by commercial area | [OA-15568](https://data.seoul.go.kr/dataList/OA-15568/S/1/datasetView.do) | foot traffic |
| Visitor-attracting facilities by commercial area | [OA-15580](https://data.seoul.go.kr/dataList/OA-15580/S/1/datasetView.do) | facility counts |
| Commercial-area change indicator | [OA-15576](https://data.seoul.go.kr/dataList/OA-15576/S/1/datasetView.do) | external benchmark only, never a feature |

Download each table as CSV. The portal publishes the store and sales tables as several files by period (the 2023, 2024 and 2025 files, plus the latest file without a year); download all of them, because the analysis covers 2023 Q1 to 2026 Q1.

| Item | Value |
|---|---|
| Files needed | 6 tables above: store (3 period files), sales (4 period files), boundaries, pedestrian traffic, facilities, change indicator (1 file each) |
| Location | `data/raw/` |
| Encoding | cp949 (the notebooks read with `ENCODING` from `config.py`) |
| File names | keep the names the portal gives. `config.py` finds each file by the table name inside its file name (`TABLE_MARKER`) and by the year in it (`FILE_SPEC`); the Korean names live only in that block |

The district-level tables on the same portal (names ending in "by district") have similar names but are not used. They are told apart by the table name, so leaving them in `data/raw/` does no harm.

Commercial-area names are not carried into any output. To get them, join `area_code` to the boundary table.
