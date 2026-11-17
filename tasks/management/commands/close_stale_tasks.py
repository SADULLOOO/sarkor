from django.core.management.base import BaseCommand

from tasks.services import close_stale_tasks


class Command(BaseCommand):
    help = "Close completed tasks that were not reviewed in time."

    def handle(self, *args, **options):
        closed = close_stale_tasks()
        self.stdout.write(f"Closed {closed} task(s).")
