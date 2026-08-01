from typing import Dict, List
import catboost as cb
import pandas as pd

FEATS = ["length", "avg_grade", "avg_abs_grade", "max_abs_grade", "grade_std", "sinuosity", "grooming"]

CAT_FEETS = ["grooming"] #categorical

DIFFICULTIES = ["novice", "easy", "intermediate", "advanced", "expert"]
DIFF_TO_ORD = {name: i for i, name in enumerate(DIFFICULTIES)}
ORD_TO_DIFF = {i: name for name, i in DIFF_TO_ORD.items()}


def baseline(avg_abs_grade: float) -> str:
    for thresh, label in ((0.10, "novice"), (0.25, "easy"), (0.40, "intermediate"), (0.55, "advanced"), (float("inf"), "expert")):
        if avg_abs_grade < thresh:
            return label
    return "expert"


def loadd(csvs: List[str]) -> pd.DataFrame:
    resorts = pd.read_csv(csvs)
    macduff = pd.concat(resorts, ignore_index=True)

    # thankyou ms hogan now i know how to use pandas!
    macduff = macduff[macduff["difficulty"].isin(DIFFICULTIES)]
    macduff = macduff[macduff["type"] == "downhill"]
    macduff["diff_ord"] = macduff["difficulty"].map(DIFF_TO_ORD)
    print(f"Loaded {len(macduff)} rows")

    if macduff.empty:
        raise ValueError("No rows.")

    return macduff


def within_one(y: List[int], y_pred: List[int]) -> float:
    correct = sum(1 for t, p in zip(y, y_pred) if abs(t-p) <= 1)
    return correct / len(y)


def evaluate(name: str, y: List[int], y_pred: List[int]) -> Dict[str, float]:
    exact = sum(1 for t, p in zip(y, y_pred) if t == p) / len(y)
    yes = within_one(y, y_pred)
    print(f"  {name} exact accuracy: {exact:.1%}, within 1 cat: {yes:.1%}")
    return {"ex_accuracy": exact, "w1_accuracy": yes}


def trainervaluator(train, test) -> None:
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
    )
    model.fit(trainx, trainy)

    cap = model.predict(testx).flatten() # flatten needed b/c Catboost returns an (N, 1) vector for some reason
    nap = test["avg_abs_grade"].apply(baseline).map(DIFF_TO_ORD).tolist()

    evaluate("Baseline", testy.tolist(), nap)
    evaluate("CatBoost", testy.tolist(), cap.tolist())


if __name__ == "__main__":
    df = loadd("skiruns.csv")

    resorts = sorted(df["resort"].unique())
    print(f"Resorts: {resorts}")

    # held out for better geberalisation
    heldout = [resorts[-1]]
    train = df[~df["resort"].isin(heldout)]
    test = df[df["resort"].isin(heldout)]

    trainervaluator(df, f"Held-out-resort split (test resort: {heldout})", train, test)
