"""Run one agent cycle from the command line.

    python manage.py run_agents

Useful for demonstrating the agents without the frontend.
"""

import json

from django.core.management.base import BaseCommand

from core.agents import run_cycle


class Command(BaseCommand):
    help = "Run one Observe - Reason - Act cycle across all five agents."

    def handle(self, *args, **options):
        for result in run_cycle():
            agent = result.pop("agent")
            self.stdout.write("")
            self.stdout.write(agent)
            self.stdout.write("-" * len(agent))
            for key, value in result.items():
                if isinstance(value, (list, dict)) and value:
                    self.stdout.write(f"  {key}:")
                    for line in json.dumps(value, indent=2).splitlines():
                        self.stdout.write(f"    {line}")
                else:
                    self.stdout.write(f"  {key}: {value}")
