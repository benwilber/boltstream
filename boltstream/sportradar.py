import requests
from django.conf import settings
from furl import furl


def get_play_by_play(game_id):
    url = (
        furl(settings.SPORTRADAR_API_ENDPOINT)
        .join(f"/nba/trial/v5/en/games/{game_id}/pbp.json")
        .url
    )
    r = requests.get(url, params={"api_key": settings.SPORTRADAR_API_KEY})
    r.raise_for_status()
    return r.json()
