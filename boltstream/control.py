import requests
from django.conf import settings
from django.urls import reverse
from furl import furl
from xmltodict import parse as parsexml


def build_url(host, path, scheme="http"):
    return furl().set(scheme=scheme, host=host, path=path).url


def build_headers(headers=None):
    if not headers:
        headers = {}
    headers.setdefault("X-RTMP-Secret", settings.RTMP_SECRET)
    return headers


def drop_stream(stream):
    data = {"app": "app", "name": stream.uuid}
    url = build_url(stream.ingest_host, reverse("drop-stream"))
    r = requests.post(url, headers=build_headers(), data=data)
    r.raise_for_status()


def fetch_info(stream):
    url = build_url(stream.ingest_host, reverse("stream-info"))
    r = requests.get(url, headers=build_headers())
    r.raise_for_status()
    info = parsexml(r.text)
    for app in info["rtmp"]["server"]["application"]:
        if app["name"] == "app" and "live" in app and "stream" in app["live"]:
            if hasattr(app["live"]["stream"], "items"):
                streams = [app["live"]["stream"]]
            else:
                streams = app["live"]["stream"]

            for s in streams:
                if s["name"] == str(stream.uuid):
                    return s
