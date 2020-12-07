from celery import shared_task
from celery.utils.log import get_task_logger
from django.db import transaction

from . import acrcloud
from .models import Stream

logger = get_task_logger(__name__)


@shared_task
@transaction.atomic
def create_acrcloud_channel(stream_pk):
    stream = Stream.objects.get(pk=stream_pk)
    if not stream.acrcloud_acr_id:
        resp = acrcloud.create_channel(stream)
        stream.acrcloud_acr_id = resp["acr_id"]
        stream.save()


@shared_task
@transaction.atomic
def delete_acrcloud_channel(stream_pk):
    stream = Stream.objects.get(pk=stream_pk)
    if stream.acrcloud_acr_id:
        acrcloud.delete_channel(stream)
        stream.acrcloud_acr_id = None
        stream.save()
