"""Background scheduler that runs the agent cycle on autopilot.

Started once from CoreConfig.ready(). Uses APScheduler's BackgroundScheduler,
which runs on its own daemon thread inside the same process as `runserver` --
no second process, no broker, and it dies with the server rather than
lingering.
"""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from django.conf import settings

logger = logging.getLogger("core.scheduler")

# Module-level guard: ready() can run more than once per process in some
# Django deployment paths (e.g. management commands that touch app config).
# Keeping the scheduler instance here means a second call to start() is a
# harmless no-op instead of a second competing thread.
_scheduler = None


def run_cycle_job():
    """The job APScheduler calls every N minutes.

    Imported lazily inside the function, not at module load time: Django
    models and agent code aren't safe to import until the app registry has
    finished loading, and this module is imported from ready() itself.
    """
    from core.agents import run_cycle

    try:
        results = run_cycle()
        logger.info("agent cycle complete: %d agents ran", len(results))
    except Exception:
        # Broad except is deliberate here: this is the top of a background
        # thread with no caller to propagate to. Anything that escapes this
        # function kills the job silently and APScheduler won't reschedule
        # it correctly -- so every exception gets logged and swallowed, and
        # the next scheduled run goes ahead regardless of this one's outcome.
        logger.exception("agent cycle raised -- will retry next cycle")


def start():
    """Start the background scheduler, once per process."""
    global _scheduler

    if _scheduler is not None:
        return  # already running in this process

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        run_cycle_job,
        trigger="interval",
        minutes=getattr(settings, "AGENT_CYCLE_MINUTES", 5),
        id="agent-cycle",
        replace_existing=True,
        max_instances=1,  # don't overlap if one cycle runs long
        coalesce=True,    # if a run was missed, run once, not N times
    )
    _scheduler.start()
    logger.info(
        "agent cycle scheduler started -- running every %s minute(s)",
        getattr(settings, "AGENT_CYCLE_MINUTES", 5),
    )
