import json

from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.db.models import Count
from django.utils.html import format_html
from django.utils.translation import gettext as _

from .models import Credit, Feed, FeedItem, Profile, Stream, User, Viewer


class LiveNow(admin.SimpleListFilter):

    title = _("Live now")
    parameter_name = "live_now"

    def lookups(self, request, model_admin):
        return (("yes", _("Yes")), ("no", _("No")))

    def queryset(self, request, queryset):
        return {
            "yes": queryset.filter(started_at__isnull=False),
            "no": queryset.filter(started_at__isnull=True),
        }.get(self.value(), queryset)


class ProfileInline(admin.StackedInline):

    model = Profile
    can_delete = False


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    inlines = (ProfileInline,)


@admin.register(Stream)
class StreamAdmin(admin.ModelAdmin):
    raw_id_fields = ("user",)
    search_fields = ("user__username", "user__profile__name", "title", "key", "uuid")
    list_display = (
        "__str__",
        "user",
        "is_active",
        "is_live",
        "started_at",
        "viewer_count",
    )
    list_filter = ("is_active", LiveNow)
    readonly_fields = (
        "key",
        "uuid",
        "acrcloud_acr_id",
        "rtmp_endpoint",
        "stream_manifest_url",
        "stream_image",
        "stream_info",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(viewer_count=Count("viewers"))

    def viewer_count(self, stream):
        return stream.viewers.count()

    viewer_count.short_description = _("Viewers")
    viewer_count.admin_order_field = "viewer_count"

    def is_live(self, stream):
        return stream.is_live

    is_live.short_description = _("Live")
    is_live.boolean = True
    is_live.admin_order_field = "started_at"

    def rtmp_endpoint(self, stream):
        return settings.RTMP_ENDPOINT

    rtmp_endpoint.short_description = _("RTMP endpoint")

    def stream_manifest_url(self, stream):
        return format_html(
            '<a href="{}">{}</a>', stream.master_manifest_url, _("Manifest URL")
        )

    stream_manifest_url.short_description = _("Manifest URL")

    def stream_image(self, stream):
        return format_html(f'<img src="{stream.image_url}?width=300" />')

    stream_image.short_description = _("Image")

    def stream_info(self, stream):
        if stream.info:
            return format_html("<pre>{}</pre>", json.dumps(stream.info, indent=2))
        return "-"

    stream_info.short_description = _("Stream info")


@admin.register(Credit)
class CreditAdmin(admin.ModelAdmin):
    raw_id_fields = ("stream", "user")
    list_display = ("user", "stream", "amount")


@admin.register(Viewer)
class ViewerAdmin(admin.ModelAdmin):
    raw_id_fields = ("stream", "viewer")
    search_fields = (
        "viewer__username",
        "stream__key",
        "stream__uuid",
        "stream__user__username",
    )
    list_display = ("viewer", "stream", "last_viewed_at")
    readonly_fields = ("viewer", "stream", "last_viewed_at")


@admin.register(Feed)
class FeedAdmin(admin.ModelAdmin):
    list_display = ("__str__", "created_at", "feed_type", "item_count")
    readonly_fields = ("uuid", "created_at", "manifest_url", "webvtt_url")
    list_filter = ("type",)
    search_fields = (
        "name",
        "streams__title",
        "streams__uuid",
        "streams__user__username",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(item_count=Count("items"))

    def feed_type(self, feed):
        return feed.type_display

    feed_type.short_description = _("Feed type")

    def item_count(self, feed):
        return feed.items.count()

    item_count.short_description = _("Items")
    item_count.admin_order_field = "item_count"

    def manifest_url(self, feed):
        return format_html('<a href="{}">{}</a>', feed.manifest_url, _("Manifest URL"))

    manifest_url.short_description = _("Manifest URL")

    def webvtt_url(self, feed):
        return format_html('<a href="{}">{}</a>', feed.webvtt_url, _("WebVTT URL"))

    webvtt_url.short_description = _("WebVTT URL")


@admin.register(FeedItem)
class FeedItemAdmin(admin.ModelAdmin):
    list_display = ("feed", "starts_at", "ends_at")
    search_fields = ("feed__name",)
    raw_id_fields = ("feed",)
