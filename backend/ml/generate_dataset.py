"""Build a synthetic training set for the Risk Agent.

Bangladesh Railway does not publish a delay dataset, so we generate one from
rules that reflect how delays actually behave on this network, then let the
model learn those relationships back from the data. Documenting the rules here
matters: it is what makes the model's behaviour explainable in a viva.

Delays get more likely when:
  - it is raining, and much more so in heavy rain
  - the train is already running late (delays compound down the line)
  - the route is long
  - it is rush hour
  - the train has many scheduled halts

Run:  venv\\Scripts\\python ml/generate_dataset.py
"""

import csv
from pathlib import Path
from random import Random

OUT = Path(__file__).resolve().parent / "delay_dataset.csv"
ROWS = 3000
SEED = 42  # fixed so the dataset is reproducible

WEATHER = ["clear", "cloudy", "light_rain", "heavy_rain"]
WEATHER_RISK = {"clear": 0.0, "cloudy": 0.03, "light_rain": 0.25, "heavy_rain": 0.60}


def build_row(rng):
    """One journey leg, with the label saying whether it ended up delayed."""
    weather = rng.choices(WEATHER, weights=[45, 30, 18, 7])[0]
    current_delay = rng.choices(
        [0, rng.randint(1, 10), rng.randint(11, 30), rng.randint(31, 90)],
        weights=[55, 22, 15, 8],
    )[0]
    distance_km = rng.randint(40, 450)
    halts = rng.randint(2, 18)
    hour = rng.randint(0, 23)
    is_rush_hour = 1 if hour in (7, 8, 9, 17, 18, 19, 20) else 0

    # Probability of a further delay, built from the factors above.
    # Existing lateness and weather dominate, which is how delays behave on a
    # single-track network: once a train slips, it keeps slipping.
    risk = 0.02
    risk += WEATHER_RISK[weather]
    risk += min(current_delay / 40, 1.0) * 0.55
    risk += (distance_km / 450) * 0.10
    risk += (halts / 18) * 0.08
    risk += 0.10 if is_rush_hour else 0.0

    # A little noise so the model sees a realistic, not perfectly separable, problem.
    risk += rng.uniform(-0.04, 0.04)
    risk = max(0.0, min(risk, 0.98))

    will_be_delayed = 1 if rng.random() < risk else 0

    return {
        "weather": weather,
        "current_delay_minutes": current_delay,
        "distance_km": distance_km,
        "scheduled_halts": halts,
        "hour_of_day": hour,
        "is_rush_hour": is_rush_hour,
        "will_be_delayed": will_be_delayed,
    }


def main():
    rng = Random(SEED)
    rows = [build_row(rng) for _ in range(ROWS)]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    delayed = sum(r["will_be_delayed"] for r in rows)
    print(f"Wrote {len(rows)} rows to {OUT.name}")
    print(f"  delayed     {delayed} ({delayed / len(rows):.1%})")
    print(f"  on schedule {len(rows) - delayed}")


if __name__ == "__main__":
    main()
