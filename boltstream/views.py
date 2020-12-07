import json
import logging
from datetime import timedelta
from socket import gethostname

from braces.views import LoginRequiredMixin
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import Count
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, RedirectView, TemplateView
from furl import furl
from webvtt import Caption, WebVTT

from .filters import StreamFilter
from .manifests import make_feed_manifest, make_master_manifest
from .models import Feed, Stream
from .permissions import require_rtmp_secret
from .responses import HttpResponseNoContent
from .tasks import create_acrcloud_channel, delete_acrcloud_channel

User = get_user_model()
logger = logging.getLogger(__name__)


api_redirect = RedirectView.as_view(
    url=f"/api/{settings.REST_FRAMEWORK['DEFAULT_VERSION']}", permanent=False
)


@never_cache
def health_check(request):
    return HttpResponse(f"OK\n{gethostname()}\n", content_type="text/plain")


class HomeView(TemplateView):

    template_name = "boltstream/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        streams = Stream.objects.live().annotate(viewer_count=Count("viewers"))

        if self.request.GET.get("search"):
            streams = StreamFilter(self.request.GET, queryset=streams).qs

        context["streams"] = streams.order_by("-viewer_count")
        return context


class UserView(DetailView):

    queryset = User.objects.active()
    template_name = "boltstream/user.html"
    context_object_name = "user"
    slug_field = "username"
    slug_url_kwarg = "username"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()

        if "stream_uuid" in self.kwargs:
            context["active_stream"] = get_object_or_404(
                user.streams.live(), uuid=self.kwargs["stream_uuid"]
            )
        else:
            context["active_stream"] = user.streams.live().first()

        if context["active_stream"]:
            host, port = self.request.get_host(), None
            if ":" in host:
                host, port = host.split(":", 1)

            context["active_channel_url"] = furl().set(
                scheme={True: "wss", False: "ws"}[self.request.is_secure()],
                host=host,
                port=port,
                path=context["active_stream"].channel_url,
            )

        return context


class ProfileView(LoginRequiredMixin, DetailView):

    queryset = User.objects.active()
    template_name = "boltstream/profile.html"
    context_object_name = "user"
    slug_field = "username"
    slug_url_kwarg = "username"


class MasterManifestView(DetailView):

    queryset = Stream.objects.live()
    slug_field = "uuid"
    slug_url_kwarg = "uuid"

    @method_decorator(never_cache)
    def get(self, request, *args, **kwargs):
        stream = self.get_object()
        manifest = make_master_manifest(request, stream)
        return HttpResponse(manifest, content_type="application/vnd.apple.mpegurl")


class FeedManifestView(DetailView):

    queryset = Feed.objects.all()
    slug_field = "uuid"
    slug_url_kwarg = "uuid"

    @method_decorator(never_cache)
    def get(self, request, *args, **kwargs):
        feed = self.get_object()
        try:
            stream = get_object_or_404(feed.streams.all(), uuid=request.GET["stream"])
        except KeyError:
            return HttpResponseBadRequest(_("Bad request"))
        manifest = make_feed_manifest(request, stream, feed)
        return HttpResponse(manifest, content_type="application/vnd.apple.mpegurl")


class FeedWebVTTView(DetailView):

    queryset = Feed.objects.all()
    slug_field = "uuid"
    slug_url_kwarg = "uuid"

    def get_vtt_timecode(self, start, end):
        msecs = int((end - start).total_seconds() * 1000)
        hours, remainder = divmod(msecs, 3600 * 1000)
        minutes, remainder = divmod(remainder, 60 * 1000)
        seconds, millis = divmod(remainder, 1000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"

    @method_decorator(never_cache)
    def get(self, request, *args, **kwargs):
        feed = self.get_object()

        try:
            stream = get_object_or_404(feed.streams.all(), uuid=request.GET["stream"])
        except KeyError:
            return HttpResponseBadRequest(_("Bad request"))

        webvtt = WebVTT()
        resp = HttpResponse(content_type="text/vtt; charset=utf-8")

        try:
            start = parse_datetime(request.GET["start"])
            end = parse_datetime(request.GET["end"])
            epoch = parse_datetime(request.GET["epoch"])
        except KeyError:
            return HttpResponseBadRequest(_("Bad request"))

        if stream.program_date_time:
            start_diff = start - stream.started_at
            end_diff = end - stream.started_at
            start = stream.program_date_time + start_diff
            end = stream.program_date_time + end_diff
            epoch = stream.program_date_time

        start = start - timedelta(seconds=5)
        end = end + timedelta(seconds=5)

        items = feed.items.filter(starts_at__gte=start, ends_at__lt=end).order_by(
            "starts_at"
        )
        for item in items:
            start_timecode = self.get_vtt_timecode(epoch, item.starts_at)
            end_timecode = self.get_vtt_timecode(epoch, item.ends_at)
            data = {
                "uuid": item.uuid,
                "starts_at": item.starts_at.isoformat(),
                "ends_at": item.ends_at.isoformat(),
                "start_timecode": start_timecode,
                "end_timecode": end_timecode,
                "payload": item.payload,
            }
            cap = Caption(
                start_timecode, end_timecode, [json.dumps(data, cls=DjangoJSONEncoder)]
            )
            webvtt.captions.append(cap)

        webvtt.write(resp)
        return resp


@never_cache
@require_rtmp_secret
def authorize_key_access(request):
    stream = get_object_or_404(
        Stream.objects.live(), uuid=request.META["HTTP_X_STREAM_UUID"]
    )
    stream.add_viewer(request.user)
    return HttpResponse(_("OK"))


@never_cache
@require_rtmp_secret
def authorize_channel_access(request):
    get_object_or_404(Stream.objects.live(), uuid=request.META["HTTP_X_STREAM_UUID"])
    return HttpResponse(_("OK"))


@csrf_exempt
@require_POST
@require_rtmp_secret
def authorize_channel_message(request):
    if request.user.is_authenticated and request.user.is_active:
        get_object_or_404(
            Stream.objects.live(), uuid=request.META["HTTP_X_STREAM_UUID"]
        )
        resp = {"message": json.loads(request.body)}
        return JsonResponse(resp)

    return HttpResponseNoContent()


@csrf_exempt
@require_POST
@require_rtmp_secret
def start_stream(request):
    key = request.POST["name"]

    with transaction.atomic():
        stream = get_object_or_404(Stream.objects.active(), key=key)
        stream.started_at = timezone.now()
        stream.ingest_host = request.META["HTTP_X_INGEST_HOST"]
        stream.save()

    create_acrcloud_channel.delay(stream.pk)
    return HttpResponseRedirect(str(stream.uuid))


@csrf_exempt
@require_POST
@require_rtmp_secret
def stop_stream(request):
    key = request.POST["name"]

    with transaction.atomic():
        stream = get_object_or_404(Stream, key=key)
        stream.started_at = None
        stream.ingest_host = None
        stream.save()

    delete_acrcloud_channel.delay(stream.pk)
    stream.expire_all_viewers()
    return HttpResponse("OK")


@csrf_exempt
@require_POST
@require_rtmp_secret
def expire_viewers(request):
    since = None
    if "since_seconds" in request.POST:
        since_seconds = int(request.POST["since_seconds"])
        since = timezone.now() - timedelta(seconds=since_seconds)

    for stream in Stream.objects.live():
        stream.expire_viewers(since=since)

    return HttpResponse(_("OK"))
