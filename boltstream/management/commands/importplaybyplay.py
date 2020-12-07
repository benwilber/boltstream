from datetime import timedelta

from django.core.management import BaseCommand
from django.utils.dateparse import parse_datetime
from django.utils.translation import gettext as _

from boltstream.models import Feed
from boltstream.sportradar import get_play_by_play


class Command(BaseCommand):

    help = _("Import play by play events from SportRadar")

    def add_arguments(self, parser):
        parser.add_argument("-f", "--feed", required=True, help=_("Feed ID"))
        parser.add_argument("game-id", help=_("SportRadar Game ID"))

    def handle(self, *args, **kwargs):
        feed = Feed.objects.get(uuid=kwargs["feed"])
        pbp = get_play_by_play(kwargs["game-id"])
        for period in pbp["periods"]:
            for event in period["events"]:
                if "wall_clock" in event:
                    starts_at = parse_datetime(event["wall_clock"])
                    ends_at = starts_at + timedelta(seconds=5)
                    item = feed.items.create(
                        starts_at=starts_at, ends_at=ends_at, payload=event
                    )
                    self.stdout.write(str(item))
