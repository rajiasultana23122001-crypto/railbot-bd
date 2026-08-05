"""Create a Station Manager login.

    python manage.py create_manager <username> [password]

Station Manager accounts are deliberately not self-service - this command is
the only way one gets created. Omit the password to be prompted for it
(not echoed to the terminal) rather than passing it on the command line
where shell history would keep it.
"""

import getpass

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError

from core.models import StationManager


class Command(BaseCommand):
    help = "Create a Station Manager login."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument(
            "password", nargs="?", default=None, help="Omit to be prompted instead."
        )

    def handle(self, *args, **options):
        username = options["username"]
        password = options["password"] or getpass.getpass("Password: ")

        if not password:
            raise CommandError("Password cannot be empty.")
        if StationManager.objects.filter(username=username).exists():
            raise CommandError(f"'{username}' already exists.")

        StationManager.objects.create(
            username=username, password_hash=make_password(password)
        )
        self.stdout.write(self.style.SUCCESS(f"Station manager '{username}' created."))
