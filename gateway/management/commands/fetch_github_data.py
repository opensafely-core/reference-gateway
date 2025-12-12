from django.core.management import BaseCommand

from ...actions import create_or_update_projects, create_or_update_users


class Command(BaseCommand):
    def handle(self, **kwargs):
        create_or_update_projects()
        create_or_update_users()
