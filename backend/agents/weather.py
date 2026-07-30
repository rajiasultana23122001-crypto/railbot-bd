"""Weather along a route, for the Risk Agent.

Simulated for now. The OpenWeatherMap call slots into current_weather() without
anything else changing: keep returning one of the four conditions the model was
trained on, and the rest of the system carries on unchanged.

To switch to live data, set OPENWEATHER_API_KEY and fill in the marked branch.
"""

import os
from random import Random

CONDITIONS = ["clear", "cloudy", "light_rain", "heavy_rain"]

# Monsoon season in Bangladesh runs June to September, so rain is weighted
# heavily here to make the demo representative rather than sunny by default.
WEIGHTS = [30, 30, 25, 15]

# Seeded per destination so the same route reports the same weather within a
# run - otherwise every refresh would change the forecast and the dashboard
# would look unstable.
_SEED_BASE = 20260731


def current_weather(location):
    """Return one of CONDITIONS for the given place."""
    api_key = os.environ.get("OPENWEATHER_API_KEY")
    if api_key:
        # Live lookup goes here. Map the API's condition codes onto CONDITIONS
        # so the model keeps receiving the vocabulary it was trained on.
        pass

    rng = Random(_SEED_BASE + sum(ord(c) for c in location))
    return rng.choices(CONDITIONS, weights=WEIGHTS)[0]
