# PisteLens

Every ski resort grades its own runs, and no two resorts do it the same way. A blue at one resort can feel like a black at another. PisteLens gives every run a **global rating** from 0 (novice) to 5 (extreme) that depends only on the run's terrain, so the number means the same thing everywhere. It can also **calibrate** that rating to a resort you know.

It includes 6,060 downhill runs across 20 resorts on five continents, all taken from OpenStreetMap. It is a Flask web app with English and French interfaces.

## Features

- **Search** runs by name or resort. You can filter by official grade, global rating, length and grooming.
- **Run pages** show the run's outline on a map, its global rating, and its rating calibrated to any resort.
- **Grade your own run** from a GPX file, or by entering its terrain features by hand.
- **Download** the dataset, the trained model and the calibration offsets.
- **Settings** let you choose a default resort to calibrate to. It is saved in your browser.

## Quick start

You need [uv](https://docs.astral.sh/uv/) and Python 3.14 or newer.

```sh
uv sync
uv run app.py
```

Then open <http://localhost:6767>. The French version starts at <http://localhost:6767/index-fr.html>.

Run `app.py` from the repository root, because it loads the model and data from `data/` using relative paths. The repo already includes a trained model and dataset, so you don't need to build anything first.

The browser needs internet access. Run pages load map tiles and run outlines from OpenStreetMap, and GPX grading looks up missing elevations online.

## How it works

### 1. Collecting runs

[build_csv.py](build_csv.py) uses the Overpass API to fetch every `piste:type` way inside each resort's bounding box. Elevations come from Open-Elevation, with Open Topo Data as a fallback. [rte_ingest.py](rte_ingest.py) then:

1. measures the distance along the run;
2. smooths the elevation profile with a 3-point moving average;
3. resamples the run into 75 m segments and works out the grade (slope) of each one.

### 2. Terrain features

[features.py](features.py) turns those segments into the seven features the model uses:

| Feature | Meaning |
| --- | --- |
| `length` | Total run length (m) |
| `avg_grade` | Length-weighted average grade (negative = downhill) |
| `avg_abs_grade` | Length-weighted average steepness |
| `max_abs_grade` | Steepest 75 m segment |
| `grade_std` | How much the steepness varies along the run |
| `sinuosity` | Distance along the run ÷ straight-line distance from start to end |
| `grooming` | `classic` (groomed), `mogul` or `backcountry` (ungroomed) |

### 3. Global rating

A LightGBM regression model maps these features to the official grade scale:

| 0 | 1 | 2 | 3 | 4 | 5 |
| --- | --- | --- | --- | --- | --- |
| novice | easy | intermediate | advanced | expert | extreme |

Training uses only downhill runs that have an official grade. [train.py](train.py) checks how well the model generalises with leave-one-resort-out testing: it trains on 19 resorts and tests on the one it held out. Averaged over all 20 resorts:

- **50.8%** of runs are given exactly their official grade.
- **94.8%** are within one grade of it.

### 4. Calibration

[calibrate.py](calibrate.py) rates every run with a model that never saw that run's resort. For each resort it then averages the gap between the official grade and that rating (`official − predicted`). Resorts with only a few runs could get extreme values by chance, so each average is shrunk toward zero by `n / (n + 10)`, where `n` is the resort's number of runs. The result is that resort's **offset**, stored in `data/calibration.json`.

A calibrated rating is `clip(global_rating − offset, 0, 5)`.

## Rebuilding the data and model

The training scripts use LightGBM's scikit-learn interface, so you need scikit-learn as well:

```sh
uv add scikit-learn
```

```sh
uv run build_csv.py   # fetch pistes and compute features → data/skiruns.csv
uv run train.py       # leave-one-resort-out evaluation (prints accuracy, saves nothing)
uv run calibrate.py   # fit the final model and offsets → calibration.txt, calibration.json, calibrated_runs.json
```

- `build_csv.py` **adds rows to the end of** `data/skiruns.csv`. Delete the old file first, or every run will appear twice.
- A full rebuild makes thousands of requests to public Overpass and elevation services and takes a long time. If they are busy, the scripts move on to the next server in their list.
- To add a resort, add its name and bounding box `(south, west, north, east)` to the `resorts` dictionary in `build_csv.py`.

## API

The frontend uses these JSON endpoints. Every endpoint that takes `ref` (a resort name from `/resortlist`) also returns a `calibrated` rating.

| Method | Path | Description |
| --- | --- | --- |
| GET | `/resortlist` | Every resort and its calibration offset |
| GET | `/runslist` | Search runs (parameters below) |
| GET | `/run/<id>` | One run by its OpenStreetMap way ID. Optional `ref` |
| POST | `/grade/feats` | Grade a run from a JSON body containing all seven features. Optional `ref` |
| POST | `/grade/gpx` | Grade an uploaded GPX file (multipart: `file`, optional `grooming` and `ref`; 50 MB max) |
| GET | `/download/<name>` | Download `skiruns.csv`, `calibrated_runs.json`, `calibration.json` or `calibration.txt` |

`/runslist` parameters: `search`, `resort`, `grade`, `grooming`, `diffmin`, `diffmax`, `lenmin`, `lenmax`, `ref`, `limit` (default 200, max 2000) and `q`.

`q` takes a small query language. Each condition is `field operator value`, and conditions are joined with ` und `:

```
resort=zermatt und global_rating>=2.5 und length>1000
name~couloir
```

- Number fields (`global_rating`, `length`, `lat`, `lon`, `id`) support `<`, `>`, `<=`, `>=` and `=`.
- Text fields (`resort`, `name`, `original_grade`, `grooming`) support `=` and `~` (contains). Text matching ignores case.

Example:

```sh
curl -X POST localhost:6767/grade/feats -H "Content-Type: application/json" \
  -d '{"length": 1142, "avg_grade": -0.19, "avg_abs_grade": 0.19, "max_abs_grade": 0.49,
       "grade_std": 0.12, "sinuosity": 1.06, "grooming": "classic", "ref": "whistler"}'
```

GPX files must contain exactly one track.

## Project layout

```
app.py            Flask server and API
rte_ingest.py     GPX parsing, elevation lookup, smoothing, 75 m resampling
features.py       Terrain feature extraction
osm.py            Overpass API queries
process_piste.py  Turns an OSM way into points and segments
build_csv.py      Builds the dataset for every resort
train.py          Model settings and leave-one-resort-out evaluation
calibrate.py      Final model, resort offsets and calibrated runs
data/             Dataset, trained model and offsets
frontend/         Static site (English pages and *-fr French pages)
```

## Limitations

The ratings are a guide, not a guarantee. They measure terrain only. Snow conditions, weather, run width, exposure and crowds all change how hard a run feels on the day. OpenStreetMap data can be incomplete, and some runs have no name or official grade.

## Credits

- Piste data © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors, available under the Open Database License.
- Elevation data from [Open-Elevation](https://open-elevation.com/) and [Open Topo Data](https://www.opentopodata.org/).
- GPX parsing by [gpxpy](https://github.com/tkrajina/gpxpy/tree/dev).
- Maps by [Leaflet](https://leafletjs.com/).
