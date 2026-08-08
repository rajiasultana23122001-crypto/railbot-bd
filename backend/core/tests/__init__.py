"""The RailBot BD test suite.

Split by what is being defended rather than by module:

    test_journeys.py  who is allowed to see which bookings
    test_auth.py      who is allowed to reach which endpoint at all
    test_agents.py    the Observe-Reason-Act loop, and that running it
                      twice does not act twice

Most of these were written against bugs this project actually had - the
Scheduler trimming the same halts on every cycle, the Manager texting the
same time over and over, a passenger token reading every other passenger's
journeys. They are here so those cannot come back quietly.

    python manage.py test
"""
