"""Management command that creates the guest account used by the frontend."""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

GUEST_EMAIL = "kevin@kovacsi.de"
GUEST_PASSWORD = "asdasdasd"


class Command(BaseCommand):
    """Create the guest user for the frontend's guest login if missing."""

    help = "Creates the guest user used by the frontend guest login."

    def handle(self, *args, **options):
        """Create the guest user unless it already exists."""
        if User.objects.filter(email=GUEST_EMAIL).exists():
            self.stdout.write("Guest user already exists.")
            return
        User.objects.create_user(
            username=GUEST_EMAIL,
            email=GUEST_EMAIL,
            password=GUEST_PASSWORD,
            first_name="Guest",
            last_name="User",
        )
        self.stdout.write(self.style.SUCCESS("Guest user created."))
