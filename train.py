from typing import Dict, List
import lightgbm as lgb
import pandas as pd
import numpy as np

FEATS = ["length", "avg_grade", "avg_abs_grade", "max_abs_grade", "grade_std", "sinuosity", "grooming"]

CAT_FEETS = ["grooming"] #categorical

DIFFICULTIES = ["novice", "easy", "intermediate", "advanced", "expert", "extreme"]
DIFF_TO_ORD = {name: i for i, name in enumerate(DIFFICULTIES)}
ORD_TO_DIFF = {i: name for name, i in DIFF_TO_ORD.items()}

def model_params() -> dict:
    # hyperparams configured using advice from many YT videos, reddit, and manual tweaking
    return dict(
        objective = "regression",
        n_estimators = 70,
        max_depth = 5, # to avoid overfitting
        num_leaves = 25,
        min_child_samples = 15,
        learning_rate = 0.07,
        colsample_bytree = 0.8,
        min_split_gain = 0.02,
        reg_alpha = 0.01,
        reg_lambda = 1,
        random_state = 67, #heeheehee
        verbose = -1
    )

def loadd(csvs: List[str]) -> pd.DataFrame:
    macduff = pd.read_csv(csvs)

    # thankyou ms hogan now i know how to use pandas!
    macduff = macduff[macduff["difficulty"].isin(DIFFICULTIES)]
    macduff = macduff[macduff["type"] == "downhill"]
    macduff = macduff[(macduff["length"] > 0) & (macduff["avg_abs_grade"] > 0) & (macduff["max_abs_grade"] > 0)]
    macduff["diff_ord"] = macduff["difficulty"].map(DIFF_TO_ORD)
    macduff["grooming"] = macduff["grooming"].astype("category")

    print(f"Loaded {len(macduff)} rows")

    if macduff.empty:
        raise ValueError("No rows.")

    return macduff


def evaluate(name: str, y: List[int], y_pred: List[int]) -> Dict[str, float]:
    acc = sum(1 for t, p in zip(y, y_pred) if t == p) / len(y)
    w1 = 0
    for a, b in zip(y, y_pred):
        if abs(a-b) <= 1:
            w1 += 1

    w1p = w1 / len(y)

    print(f"[{name}] accuracy: {acc:.1%}. Accuracy within 1 category: {w1p:.1%}")
    return {"ex_acc": acc, "w1_acc": w1p}


def trainervaluator(train: pd.DataFrame, test: pd.DataFrame, heldout: str) -> Dict[str, float]:
    print(f"Training rows: {len(train)}. Testing rows: {len(test)}. Held out resort: {heldout}")

    trainx = train[FEATS]
    trainy = train["diff_ord"]
    testx = test[FEATS]
    testy = test["diff_ord"]

    model = lgb.LGBMRegressor(**model_params())
    model.fit(trainx, trainy, categorical_feature = CAT_FEETS)

    cap_cont = model.predict(testx)
    cap = np.clip(np.rint(cap_cont), 0, len(DIFFICULTIES)-1).astype(int)

    bonk = evaluate("LightGBM", testy.tolist(), cap.tolist())
    bonk["continuous"] = cap_cont.tolist()

    return bonk


if __name__ == "__main__":
    df = loadd("data/skiruns.csv")

    resorts = sorted(df["resort"].unique())
    print(f"Resorts: {resorts}")

    # held out for better geberalisation
    monkey_ex = 0
    monkey_w1 = 0
    for n in range(len(resorts)):
        heldout = [resorts[n]]
        train = df[~df["resort"].isin(heldout)]
        test = df[df["resort"].isin(heldout)]

        result = trainervaluator(train, test, resorts[n])
        monkey_ex += result["ex_acc"]
        monkey_w1 += result["w1_acc"]

    monkey_ex = monkey_ex / len(resorts)
    monkey_w1 = monkey_w1 / len(resorts)
    print(f"Average accuracy: {monkey_ex:.1%} (exact), {monkey_w1:.1%} (within 1 category)")
