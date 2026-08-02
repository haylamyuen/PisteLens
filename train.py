from typing import Dict, List
import catboost as cb
import pandas as pd

FEATS = ["length", "avg_grade", "avg_abs_grade", "max_abs_grade", "grade_std", "sinuosity", "grooming"]

CAT_FEETS = ["grooming"] #categorical

DIFFICULTIES = ["novice", "easy", "intermediate", "advanced", "expert", "extreme"]
DIFF_TO_ORD = {name: i for i, name in enumerate(DIFFICULTIES)}
ORD_TO_DIFF = {i: name for name, i in DIFF_TO_ORD.items()}


def baseline(avg_abs_grade: float) -> str:
    for thresh, label in ((0.10, "novice"), (0.25, "easy"), (0.40, "intermediate"), (0.55, "advanced"), (0.70, "expert"), (float("inf"), "extreme")):
        if avg_abs_grade < thresh:
            return label
    return "extreme"


def loadd(csvs: List[str]) -> pd.DataFrame:
    macduff = pd.read_csv(csvs)

    # thankyou ms hogan now i know how to use pandas!
    macduff = macduff[macduff["difficulty"].isin(DIFFICULTIES)]
    macduff = macduff[macduff["type"] == "downhill"]
    macduff = macduff[(macduff["length"] > 0) & (macduff["avg_abs_grade"] > 0) & (macduff["max_abs_grade"] > 0)]
    macduff["diff_ord"] = macduff["difficulty"].map(DIFF_TO_ORD)
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

    model = cb.CatBoostClassifier(
        loss_function = "MultiClass",
        iterations = 100,
        depth = 4, # to avoid overfitting
        min_data_in_leaf = 5,
        cat_features = CAT_FEETS,
        random_state = 67, #heeheehee
        verbose = False
    )
    model.fit(trainx, trainy)

    cap = model.predict(testx).flatten() # flatten needed b/c Catboost returns a (N, 1) vector for some reason
    nap = test["avg_abs_grade"].apply(baseline).map(DIFF_TO_ORD).tolist()

    evaluate("Baseline", testy.tolist(), nap)
    bonk = evaluate("CatBoost", testy.tolist(), cap.tolist())

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
