"""The RailBot BD test suite.

Split by what is being defended rather than by module:

    test_journeys.py  who is allowed to see which bookings
    test_auth.py      who is allowed to reach which endpoint at all
    test_agents.py    the Observe-Reason-Act loop, and that running it
                      twice does not act twice
    test_risk.py      the Risk Agent, with the model stubbed out
    test_delays.py    the doorway - what POST /api/delays accepts, and
                      what one report is supposed to change
    test_contract.py  the JSON key names the React dashboards are
                      written against

Most of these were written against bugs this project actually had - the
Scheduler trimming the same halts on every cycle, the Manager texting the
same time over and over, a passenger token reading every other passenger's
journeys. They are here so those cannot come back quietly.

Six tests currently fail on purpose. Each is marked EXPECTED FAILURE in its
own docstring and describes the bug it found rather than the behaviour that
exists, because a test written to match a bug is worse than no test at all.
See BUGS.md for the list and the suggested fixes.

    python manage.py test
"""
