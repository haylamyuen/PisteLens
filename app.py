import json
from typing import Dict, List, Tuple
import os
import pandas as pd
import lightgbm as lgb
import numpy as np
import tempfile
from flask import Flask, jsonify, request, send_from_directory

from train import FEATS
from features import compute_feats
from rte_ingest import process_points
from rte_ingest import parse
from calibrate import calibrate

# CONFIGG

app = Flask(__name__, static_folder = "frontend", static_url_path = "")
app.config["MAX_CONTENT_LENGTH"] = 50*1024*1024 #50megs

STATE = {"model": None, "offsets": {}, "runs": None, "meta": {}}

def loader() -> None:
    with open("data/calibration.json") as andy:
        meta = json.load(andy)
    
    STATE["offsets"] = meta.get("offsets", {})
    STATE["meta"] = meta
    STATE["model"] = lgb.Booster(model_file="data/calibration.txt")

    runs = pd.read_json("data/calibrated_runs.json", orient = "records")

    missing = [col for col in ("length", "grooming") if col not in runs.columns]
    if missing:
        extra = pd.read_csv("data/skiruns.csv", usecols=["id"]+missing)
        runs = runs.merge(extra, on="id", how="left")

    STATE["runs"] = runs
    
    print(f"Loaded model and {len(runs)} runs.")


# GOOFY AHH PARSING

allowed_operators = ["<=", ">=", "<", ">", "=", "~"]
num_fields = {"global_rating", "id", "lat", "lon", "length"} # used set so that we can use bitwise or for union
str_fields = {"resort", "name", "original_grade", "grooming"}

def qparse(thingo: str) -> Tuple[str, str, str]:
    for op in allowed_operators:
        if op in thingo:
            field, value = thingo.split(op, 1)
            return field.strip().strip("'\""), op, value.strip().strip("'\"")
    raise ValueError("Could not parse query.")

def query(df: pd.DataFrame, query: str) -> pd.DataFrame:
    for thingo in query.split(" und "):
        thingo = thingo.strip()

        field, op, value = qparse(thingo)
        if field in num_fields:
            try:
                v = float(value)
                match op:
                    case "<": df = df[df[field] < v]
                    case ">": df = df[df[field] > v]
                    case "<=": df = df[df[field] <= v]
                    case ">=": df = df[df[field] >= v]
                    case "=": df = df[df[field] == v]
                    case _: raise ValueError("Operator not allowed on numerical data.")
            except ValueError:
                raise ValueError(f"{field} requires a number value after the operator.")
        elif field in str_fields:
            match op:
                case "=": df = df[df[field].astype("string").str.lower() == value.lower()]
                case "~": df = df[df[field].astype("string").str.lower().str.contains(value.lower(), na=False, regex=False)]
                case _: raise ValueError("Operator not allowed on text data.")
        else:
            raise ValueError(f"Unknown field '{field}'. Allowed: {num_fields | str_fields}.")
    
    return  df

def add_calib(records: List[Dict], ref: str) -> None:
    offset = STATE["offsets"][ref]
    for donkey in records:
        donkey["ref"] = ref
        donkey["calibrated"] = round(calibrate(donkey["global_rating"], offset), 2)

downloadable = {"skiruns.csv", "calibration.txt", "calibration.json", "calibrated_runs.json"}

@app.get("/download/<name>")
def download(name: str):
    if name not in downloadable:
        return jsonify({"error": "file not available"}), 404
    return send_from_directory("data", name, as_attachment=True)

@app.get("/resortlist")
def resortlist():
    items = [{"resort": yes, "offset": round(no, 3)} for yes, no in sorted(STATE["offsets"].items())]
    return jsonify({"resorts": items, "count": len(items)})

@app.get("/run/<int:run_id>")
def one_run(run_id: int):
    if STATE["runs"] is None:
        return jsonify({"error": "no runs loaded"}), 503

    rows = STATE["runs"][STATE["runs"]["id"] == run_id].to_dict(orient ="records")
    if not rows:
        return jsonify({"error": "run not found"}), 404

    ref = request.args.get("ref")
    if ref:
        if ref not in STATE["offsets"]:
            return jsonify({"error": "unknown reference resort. see /resortlist"}), 400
        add_calib(rows, ref)

    return jsonify(rows[0])

@app.get("/runslist")
def runlikeyourbeingeatenbyamoose():
    if STATE["runs"] is None:
        return jsonify({"error": "no runs loaded"}), 503
    df = STATE["runs"]

    if request.args.get("search"):
        a = request.args["search"].lower()
        b = lambda col: df[col].astype("string").str.lower().str.contains(a, na=False, regex=False) # this line was made with help by claude
        df = df[b("name") | b("resort")] # merge
    
    thingos = []
    if request.args.get("resort"):
        thingos.append(f"resort={request.args['resort']}")
    if request.args.get("diffmin"):
        thingos.append(f"global_rating>={request.args['diffmin']}")
    if request.args.get("diffmax"):
        thingos.append(f"global_rating<={request.args['diffmax']}")

    if request.args.get("lenmin"):
        thingos.append(f"length>={request.args['lenmin']}")
    if request.args.get("lenmax"):
        thingos.append(f"length<={request.args['lenmax']}")
    if request.args.get("grade"):
        thingos.append(f"original_grade={request.args['grade']}")

    if request.args.get("grooming"):
        thingos.append(f"grooming={request.args['grooming']}")

    if request.args.get("q"):
        thingos.append(request.args["q"])
    
    try:
        if thingos:
            df = query(df, " und ".join(thingos))
        limit = min(int(request.args.get("limit", 200)), 2000)

    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    yesnt = len(df)
    
    page = df.iloc[0:limit]
    records = page.to_dict(orient =  "records")
    ref = request.args.get("ref")
    
    if ref:
        if ref not in STATE["offsets"]:
            return jsonify({"error": "unknown reference resort. see /resortlist"})
        add_calib(records, ref)
    
    return jsonify({
        "count": len(records),
        "matches": yesnt,
        "limit": limit,
        "ref": ref,
        "runs": records
    })

@app.post("/grade/feats")
def grade_these_feets() :
    jason = request.get_json(silent=True)
    missing_dinosaurs = [funky for funky in FEATS if funky not in jason]

    if missing_dinosaurs:
        return jsonify({"error": f"missing feature(s): {missing_dinosaurs}"})

    else:
        try:
            brachiosaurus = pd.DataFrame([{funky: jason[funky] for funky in FEATS}])
            brachiosaurus["grooming"] = brachiosaurus["grooming"].astype("category")
            terrain = float(STATE["model"].predict(brachiosaurus)[0])
        except:
            return jsonify({"error": "run grading failed :("}), 400
        
        result = {"global_rating": round(np.clip(terrain, 0, 5),2)}
        if jason.get("ref"):
            if jason.get("ref") not in STATE["offsets"]:
                return jsonify({"error": "unknown reference resort. see /resortlist"})
            result["ref"] = jason.get("ref")
            result["calibrated"] =round(calibrate(terrain, STATE["offsets"][jason.get("ref")]), 2)
        
        return jsonify(result)

@app.post("/grade/gpx")
def grade_gpx():
    andy = request.files.get("file")
    if not andy or not andy.filename:
        return jsonify({"error": "ensure a file is provided"}), 400
    
    ref = request.form.get("ref")
    if ref:
        if ref not in STATE["offsets"]:
            return jsonify({"error": "unknown reference resort. see /resortlist"})
    groom = request.form.get("grooming", "classic")

    brot = tempfile.NamedTemporaryFile(suffix=".gpx", delete=False)
    brot.close()

    try:
        andy.save(brot.name)
        pts = parse(brot.name)
        segs = process_points(pts, potato=andy.filename)
        feets = compute_feats(pts, segs, grooming=groom)
    except:
        return jsonify({"error": "processing failed."}), 500
    finally:
        os.remove(brot.name)
        
    isaac = pd.DataFrame([{k: feets[k] for k in FEATS}])
    isaac["grooming"] = isaac["grooming"].astype("category")
    terrain = float(STATE["model"].predict(isaac)[0])
    result = {"filename": andy.filename, "global_rating": round(np.clip(terrain,0,5),2)}

    if ref:
        result["ref"] = ref
        result["calibrated"] = round(calibrate(terrain, STATE["offsets"][ref]), 2)


    return jsonify(result)



@app.get("/")
def home():
    return app.send_static_file("index.html")

@app.errorhandler(413)
def toobig(e):
    return jsonify({"error": "file exceeds 50MB limit."}), 413

loader()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6767, debug=False)

