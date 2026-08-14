import os

from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        # Observers are registered unconditionally, and before the guard
        # below. The audit trail is one of them, so an agent that ran with
        # nothing subscribed would act and leave no record - and that
        # includes every agent the test suite runs, where RUN_MAIN is unset.
        # subscribe() ignores a duplicate, so a second ready() is harmless.
        from core.events import register_default_observers
        register_default_observers()

        # runserver's auto-reloader forks a watcher process and a real one;
        # RUN_MAIN is only set in the real one. Without this guard the
        # scheduler starts twice and the agent cycle runs in duplicate.
        # RUN_MAIN is unset entirely under gunicorn/uwsgi, so this also
        # correctly starts the scheduler exactly once there.
        if os.environ.get('RUN_MAIN') != 'true':
            return

        from core.scheduler import start
        start()
