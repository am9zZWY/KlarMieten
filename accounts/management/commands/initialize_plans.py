# accounts/management/commands/initialize_plans.py

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Initialize products, plans, and capabilities for the subscription system'

    def handle(self, *args, **options):
        self.stdout.write('Creating products, capabilities and plans...')

        # Only initialize if the database is ready and no plans exist yet
        from django.db import connections
        from django.db.utils import OperationalError
        try:
            conn = connections['default']
            conn.cursor()

            # Check if we need to initialize
            from accounts.models import Plan
            if Plan.objects.count() == 0:
                from accounts.utils import initialize_system
                initialize_system()

        except OperationalError:
            # Database isn't ready yet
            pass

        self.stdout.write(self.style.SUCCESS('Successfully initialized subscription system'))
