from typing import Dict
import json
import numpy as np
import lightgbm as lgb
import pandas as pd

from train import model_params, loadd, FEATS, CAT_FEETS, DIFFICULTIES

def terrain_grade(df: pd.DataFrame) -> np.ndarray:
    ratings = np.full(len(df), np.nan)
    resorts = sorted(df["resort"].unique())
    pos = {cheese: i for i, cheese in enumerate(df.index)} # because index might not be the same as position

    for r in resorts:
        train = df[df["resort"] != r]
        test = df[df["resort"] == r]

        model = lgb.LGBMRegressor(**model_params())
        model.fit(train[FEATS], train["diff_ord"], categorical_feature = CAT_FEETS)
        preds = model.predict(test[FEATS])

        for cheese, pred in zip(test.index, preds):
            ratings[pos[cheese]] = pred*1.05

    return ratings

def comp_offset(df: pd.DataFrame, rating: np.ndarray) -> pd.DataFrame:
    spatzel = df[["resort", "diff_ord"]].copy()
    spatzel["rating"] = rating
    spatzel["resid"] = spatzel["diff_ord"] - spatzel["rating"]

    pretzel = spatzel.groupby("resort")["resid"]
    quarkballschen = pd.DataFrame({"n": pretzel.size(), "roffset": pretzel.mean()} )
    quarkballschen["offset"] = ((quarkballschen["n"]) / (quarkballschen["n"]+10)) * quarkballschen["roffset"] # penalises small dataset
    
    return quarkballschen.sort_values("offset", ascending=False)

def calibrate(rating: float, offset: float) -> float:
    return float(np.clip(rating-offset,0,5))

def build_calibrate() -> Dict:
    df = loadd("data/skiruns.csv").reset_index(drop=True)

    print("Computing Terrain Ratings...")
    terrain = terrain_grade(df)

    offsets = comp_offset(df, terrain)
    print("Computed Offsets:")  
    print(offsets.to_string())

    print("\nFitting the model...")
    model = lgb.LGBMRegressor(**model_params())
    model.fit(df[FEATS], df["diff_ord"], categorical_feature = CAT_FEETS)
    model.booster_.save_model("data/calibration.txt") # save model so that its faster when called from flask

    runs = pd.DataFrame({
        "id": df["id"],
        "resort": df["resort"],
        "name": df.get("name", pd.Series([""]*len(df))).fillna(""), #not every run has a name :(
        "original_grade": df["difficulty"],
        "lat": df["lat"],
        "lon": df["lon"],
        "length": df["length"],
        "global_rating": np.round(np.clip(terrain, 0,5), 2)
    })
    runs.to_json("data/calibrated_runs.json", orient = "records")
    print(f"Wrote {len(runs)} calibrated runs to data/calibrated_runs.json")

    info = {
        "offsets": offsets["offset"].to_dict(),
        "offset_detail": offsets.reset_index().to_dict(orient = "records"),
        "difficulties": DIFFICULTIES,
        "feats": FEATS
    }
    with open("data/calibration.json", "w", encoding="utf-8") as andy:
        json.dump(info, andy, indent=2)
    print("Wrote calibration.json")
    
    return info

def grade_run(features: Dict, offsets: Dict[str, float], model: lgb.Booster, ref: str = "donkey")  -> Dict:
    x = pd.DataFrame([features])[FEATS]
    x["grooming"] = x["grooming"].astype("category")
    terrain = float(model.predict(x)[0])
    resultt = {"global_rating": round(np.clip(terrain, 0, 5), 2)}

    if ref != "donkey":
        off = offsets.get(ref, 0)
        resultt["ref_resort"] = ref
        resultt["calibrated"] = round(calibrate(terrain, off), 2)
    
    return resultt

if __name__ == "__main__":
    build_calibrate()

