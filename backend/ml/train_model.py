"""Train the Risk Agent's delay-prediction model.

A random forest over six features. It is a small, well-understood model that
handles the mix of numeric and categorical inputs without much preprocessing,
and can report which features it leaned on — useful when explaining why the
agent flagged a particular train.

Run:  venv\\Scripts\\python ml/train_model.py
"""

from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

HERE = Path(__file__).resolve().parent
DATASET = HERE / "delay_dataset.csv"
MODEL_PATH = HERE / "risk_model.pkl"

CATEGORICAL = ["weather"]
NUMERIC = [
    "current_delay_minutes",
    "distance_km",
    "scheduled_halts",
    "hour_of_day",
    "is_rush_hour",
]
TARGET = "will_be_delayed"


def main():
    if not DATASET.exists():
        raise SystemExit(
            f"{DATASET.name} not found. Run generate_dataset.py first."
        )

    frame = pd.read_csv(DATASET)
    features = frame[CATEGORICAL + NUMERIC]
    labels = frame[TARGET]

    # stratify keeps the delayed/on-time balance the same in both splits.
    x_train, x_test, y_train, y_test = train_test_split(
        features, labels, test_size=0.2, random_state=42, stratify=labels
    )

    # Weather is a category, so it is one-hot encoded; the rest pass through.
    model = Pipeline(
        steps=[
            (
                "prepare",
                ColumnTransformer(
                    [("weather", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL)],
                    remainder="passthrough",
                ),
            ),
            (
                "forest",
                RandomForestClassifier(
                    n_estimators=200,
                    max_depth=8,
                    min_samples_leaf=5,
                    random_state=42,
                    class_weight="balanced",
                ),
            ),
        ]
    )

    model.fit(x_train, y_train)

    predictions = model.predict(x_test)
    probabilities = model.predict_proba(x_test)[:, 1]

    print("Risk Agent model")
    print(f"  training rows {len(x_train)}")
    print(f"  test rows     {len(x_test)}")
    print(f"  accuracy      {accuracy_score(y_test, predictions):.3f}")
    print(f"  roc auc       {roc_auc_score(y_test, probabilities):.3f}")
    print()
    print(classification_report(y_test, predictions, target_names=["on time", "delayed"]))

    joblib.dump(model, MODEL_PATH)
    print(f"Saved model to {MODEL_PATH.name}")


if __name__ == "__main__":
    main()
