import hmac
import time
from base64 import b64encode
from hashlib import sha1

import requests
from django.conf import settings
from furl import furl


def get_signature(message):
    access_secret = settings.ACRCLOUD_CONSOLE_ACCESS_SECRET
    signature = hmac.new(access_secret.encode(), message.encode(), digestmod=sha1)
    return b64encode(signature.digest())


def get_message(method, api_path, timestamp):
    return "\n".join(
        (
            method,
            api_path,
            settings.ACRCLOUD_CONSOLE_ACCESS_KEY,
            settings.ACRCLOUD_API_SIGNATURE_VERSION,
            timestamp,
        )
    )


def get_signed_headers(signature, timestamp):
    return {
        "access-key": settings.ACRCLOUD_CONSOLE_ACCESS_KEY,
        "signature-version": settings.ACRCLOUD_API_SIGNATURE_VERSION,
        "signature": signature,
        "timestamp": timestamp,
    }


def get_headers(method, api_path):
    timestamp = str(time.time())
    message = get_message(method, api_path, timestamp)
    signature = get_signature(message)
    return get_signed_headers(signature, timestamp)


def get_api_url(api_path):
    return furl(settings.ACRCLOUD_API_ENDPOINT).join(api_path).url


def get_all_channels():
    api_path = f"/v1/buckets/{settings.ACRCLOUD_BUCKET_NAME}/channels"
    headers = get_headers("GET", api_path)
    url = get_api_url(api_path)

    r = requests.get(url, headers=headers, verify=True)
    r.raise_for_status()
    return r.json()


def get_channel(stream):
    if not stream.acrcloud_acr_id:
        return None

    api_path = f"/v1/channels/{stream.acrcloud_acr_id}"
    headers = get_headers("GET", api_path)
    url = get_api_url(api_path)

    r = requests.get(url, headers=headers, verify=True)
    r.raise_for_status()
    return r.json()


def create_channel(stream):
    api_path = "/v1/channels"
    headers = get_headers("POST", api_path)
    url = get_api_url(api_path)
    data = {
        "url": f"rtmp://127.0.0.1:1935/live/{stream.uuid}",
        "title": str(stream),
        "channel_id": str(stream.uuid),
        "bucket_name": settings.ACRCLOUD_BUCKET_NAME,
        "custom_key[]": ["stream_uuid", "started_at"],
        "custom_value[]": [str(stream.uuid), stream.started_at.isoformat()],
    }

    r = requests.post(url, headers=headers, data=data, verify=True)
    r.raise_for_status()
    return r.json()


def update_channel(stream):
    api_path = f"/v1/channels/{stream.acrcloud_acr_id}"
    headers = get_headers("POST", api_path)
    url = get_api_url(api_path)

    data = {
        "url": f"rtmp://127.0.0.1:1935/live/{stream.uuid}",
        "title": str(stream),
        "channel_id": str(stream.uuid),
        "custom_key[]": ["stream_uuid", "started_at"],
        "custom_value[]": [str(stream.uuid), stream.started_at.isoformat()],
    }

    r = requests.put(url, headers=headers, data=data, verify=True)
    r.raise_for_status()
    return r.json()


def delete_channel(stream):
    api_path = f"/v1/channels/{stream.acrcloud_acr_id}"
    headers = get_headers("DELETE", api_path)
    url = get_api_url(api_path)
    r = requests.delete(url, headers=headers, verify=True)
    r.raise_for_status()
