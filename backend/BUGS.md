# Week 8 — bugs found by the test suite

Six tests in `core/tests/` fail on purpose. Each asserts what the system
*should* do; the code currently does something else. They are listed here
worst-first.

Run them with:

```bash
python manage.py test
```

---

## 1. A delay only reaches one passenger on the train

**Test:** `test_delays.DelayReachesEveryPassengerTests`
**File:** `core/views.py` → `report_delay`

```python
booking = Booking.objects.select_related("train").filter(train__number=train_no).first()
```

`.first()` takes one row. Two people booked on Subarna Express, a delay
reported against it, and only one of them is marked delayed — so only one
appears to the Manager Agent, which selects on `status="delayed"`. The other
passenger is never texted and their dashboard still reads on-time.

The seed data hides this: every seeded passenger is on different trains. It
shows the moment two bookings share one train, which is the ordinary case in
production.

**Fix:** loop the queryset instead of taking `.first()`. Nothing downstream
changes — the agents already handle any number of delayed bookings. Keep one
booking aside for the `reported` block in the response, since that echo is
per-train, not per-passenger.

---

## 2. The arrivals board never learns about the delay

**Test:** `test_delays.ArrivalsBoardStaysCurrentTests`
**File:** `core/views.py` → `report_delay`

`Arrival` is written by `seed.py` and read by `views.station`. Nothing else
in the codebase touches it — no view, no agent. Report a delay on train 701
and the Station Master Panel shows a delayed booking next to an arrivals row
that still says on-time, for the same train.

This is precisely the failure the architecture slide claims one call
returning the whole station prevents. Returning the numbers together makes
them arrive at the same moment; it does not make them agree.

**Fix:** the Scheduler Agent is the natural owner, since it already holds
expected departure times. Have it update matching `Arrival` rows alongside
the booking. Updating them directly in `report_delay` also works and is
smaller, but leaves arrivals frozen when a cycle runs on the timer rather
than from a report.

---

## 3. One bad platform row takes down the whole cycle

**Test:** `test_contract.ResourceAgentEdgeTests`
**File:** `core/agents/resource_agent.py` → `observe`

```python
percent = round((platform.occupancy / platform.capacity) * 100)
```

`capacity` has no default and no validator, so a `0` can be saved from the
admin. When it is, `observe()` raises `ZeroDivisionError`, which escapes
`run_cycle()` — and because the Resource Agent runs fourth, it takes the
Advisor Agent down with it. `views.report_delay` only catches
`FileNotFoundError`, so the request 500s.

**Fix:** either a `MinValueValidator(1)` on the field, or skip non-positive
capacities in `observe()`. Worth doing both — the validator stops the bad
row, the skip stops one surviving row from being fatal.

---

## 4. Platform 1 gets blamed for platform 10's crowding

**Test:** `test_contract.AdvisorPatternTests`
**File:** `core/agents/advisor_agent.py` → `reason`

```python
if log.agent == "Resource Agent" and f"Platform {platform.number}" in log.message
```

`"Platform 1"` is a substring of `"Platform 10"`. At a station with ten or
more platforms, every alert about 10, 11 or 12 also counts against platform
1, which then gets recommended for a timetable change it did not earn.

Six platforms are seeded, so nothing has gone wrong yet. Kamalapur has more
than six.

**Fix:** short-term, match on a word boundary with `re`. Better: stop parsing
message text and give `AgentLog` a nullable FK to `Platform`, so the count is
a query rather than a string search.

---

## 5. `{"minutes": true}` is accepted as a one-minute delay

**Test:** `test_delays.ReportDelayValidationTests.test_a_boolean_is_not_a_number_of_minutes`
**File:** `core/views.py` → `report_delay`

`int(True)` is `1`, and `1` is inside the 1–300 range, so a boolean posted
into the minutes field passes every check and books a one-minute delay.

**Fix:** reject `bool` explicitly before the `int()` call —
`isinstance(raw_minutes, bool)` is `True` for booleans and `False` for real
ints, which is the one case Python's numeric tower makes awkward.

---

## 6. A missing train reports as an unknown train

**Test:** `test_delays.ReportDelayValidationTests.test_a_null_train_reads_as_no_train_selected`
**File:** `core/views.py` → `report_delay`

```python
train_no = str(payload.get("trainNo", "")).strip()
```

When the frontend posts `trainNo: null` — an unset dropdown — `str(None)`
produces the string `"None"`, which is truthy, so the "Pick a train first"
branch is skipped and the request travels to the database lookup. The station
master gets *No booked journey on train None.*

**Fix:** coerce `None` to `""` before `str()`, or check `payload.get("trainNo")`
for `None` first.

---

## Not bugs, but worth knowing

- **`weather.py` is still simulated.** `current_weather()` reads
  `OPENWEATHER_API_KEY`, and the live branch is an empty `pass` — so setting
  the key changes nothing and the seeded random still answers. That is fine
  as a stub, but the Use Case diagram lists OpenWeatherMap as an external
  system, so say "simulated" if asked.
- **`_model` in `risk_agent.py` is cached in a module global** and never
  cleared. Retraining the model requires a server restart to take effect.
