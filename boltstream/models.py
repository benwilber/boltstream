from datetime import timedelta
from functools import partial
from uuid import uuid4

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db import models, transaction
from django.db.models import F, Q
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.functional import cached_property
from django.utils.text import slugify
from django.utils.translation import gettext as _
from jsonfield import JSONField

from .control import drop_stream, fetch_info

make_stream_key = partial(get_random_string, 20)


class UserManager(DjangoUserManager):
    def get_by_natural_key(self, uuid):
        try:
            return self.get(uuid=uuid)
        except ValueError:
            return super().get_by_natural_key(uuid)

    def active(self):
        return self.filter(is_active=True)

    def staff(self):
        return self.active().filter(is_staff=True)

    def superusers(self):
        return self.active().filter(is_superuser=True)

    def privileged(self):
        q = Q(is_staff=True) | Q(is_superuser=True)
        return self.active().filter(q)

    def live(self):
        return self.active().filter(
            streams__is_active=True, streams__started_at__isnull=False
        )


class User(AbstractUser):

    USERNAME_FIELD = "username"

    uuid = models.UUIDField(
        default=uuid4, unique=True, editable=False, verbose_name=_("UUID")
    )

    objects = UserManager()

    class Meta:
        swappable = "AUTH_USER_MODEL"

    def __str__(self):
        return self.get_full_name() or self.username

    def natural_key(self):
        return (self.uuid,)

    @property
    def is_privileged(self):
        return self.is_active and (self.is_staff or self.is_superuser)

    def get_absolute_url(self):
        return reverse("user", kwargs={"username": self.username})

    def get_full_name(self):
        return self.profile.name or super().get_full_name()


class ProfileManager(models.Manager):
    def get_by_natural_key(self, user_uuid):
        return self.get(user__uuid=user_uuid)


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, related_name="profile", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=200, null=True, blank=True)

    objects = ProfileManager()

    def __str__(self):
        return str(self.user)

    def natural_key(self):
        return (self.user.uuid,)

    natural_key.dependencies = (settings.AUTH_USER_MODEL,)

    def get_absolute_url(self):
        return reverse("profile", kwargs={"username": self.user.username})


class StreamManager(models.Manager):
    def get_by_natural_key(self, uuid):
        return self.get(uuid=uuid)

    def active(self):
        return self.filter(is_active=True, user__is_active=True)

    def live(self):
        return self.active().filter(started_at__isnull=False)


class Stream(models.Model):

    uuid = models.UUIDField(
        default=uuid4, unique=True, editable=False, verbose_name=_("UUID")
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="streams", on_delete=models.CASCADE
    )
    key = models.CharField(
        max_length=20,
        default=make_stream_key,
        unique=True,
        editable=False,
        verbose_name=_("Stream key"),
    )
    title = models.CharField(max_length=500, null=True, blank=True)
    ingest_host = models.CharField(max_length=200, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, verbose_name=_("Created"))
    started_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Started"))
    program_date_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Program Date Time"),
        help_text=_(
            "The original #EXT-X-PROGRAM-DATE-TIME from the HLS manifest "
            "used to calculate synchronization offsets."
        ),
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))
    credits_used = models.PositiveIntegerField(default=0)
    acrcloud_acr_id = models.CharField(
        verbose_name=_("ACRCloud ACR ID"),
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
    )
    feeds = models.ManyToManyField("Feed", related_name="streams", blank=True)

    objects = StreamManager()

    class Meta:
        ordering = ("created_at",)

    def __str__(self):
        if self.title:
            return self.title

        index = list(self.user.streams.values_list("pk", flat=True)).index(self.pk) + 1
        return f"{self.user} #{index}"

    def natural_key(self):
        return (self.uuid,)

    def get_absolute_url(self):
        return reverse(
            "stream",
            kwargs={
                "username": self.user.username,
                "stream_uuid": self.uuid,
                "stream_slug": slugify(str(self)),
            },
        )

    def drop(self):
        drop_stream(self)

    def rotate_key(self):
        if self.is_live:
            self.drop()
        self.key = make_stream_key()
        self.save()

    def expire_viewers(self, since=None):
        if since is None:
            since = timezone.now() - timedelta(seconds=settings.EXPIRE_VIEWER_SECONDS)
        self.viewers.filter(last_viewed_at__lte=since).delete()

    def expire_all_viewers(self):
        self.viewers.all().delete()

    def add_viewer(self, user):
        _, created = Viewer.objects.update_or_create(
            stream=self, viewer=user, defaults={"last_viewed_at": timezone.now()}
        )
        return created

    @property
    def is_live(self):
        return self.is_active and self.started_at is not None

    @property
    def master_manifest_url(self):
        return reverse("master-manifest", args=(self.uuid,))

    @property
    def index_manifest_url(self):
        return reverse("index-manifest", args=(self.uuid,))

    @property
    def image_url(self):
        return reverse("stream-image", args=(self.uuid,))

    @property
    def preview_url(self):
        return reverse("stream-preview", args=(self.uuid,))

    @property
    def channel_url(self):
        return reverse("stream-channel", args=(self.uuid,))

    @property
    def offline_url(self):
        return reverse("stream-offline")

    @cached_property
    def info(self):
        if self.is_live:
            return fetch_info(self)

    @transaction.atomic
    def use_credits(self, user, amount=1):
        ok = (
            self.credits.filter(user=user, amount__gte=amount).update(
                amount=F("amount") - amount
            )
            > 0
        )
        if ok:
            Stream.objects.filter(pk=self.pk).update(
                credits_used=F("credits_used") + amount
            )
        return ok


class StreamSessionManager(models.Manager):
    def get_by_natural_key(self, uuid):
        return self.get(uuid=uuid)


class StreamSession(models.Model):

    uuid = models.UUIDField(
        default=uuid4, unique=True, editable=False, verbose_name=_("UUID")
    )
    stream = models.ForeignKey(
        Stream, related_name="sessions", on_delete=models.CASCADE
    )
    started_at = models.DateTimeField(default=timezone.now, verbose_name=_("Started"))
    stopped_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Stopped"))
    ingest_host = models.CharField(max_length=200, null=True, blank=True)

    objects = StreamSessionManager()

    class Meta:
        ordering = ("started_at", "stopped_at")

    def __str__(self):
        return str(self.stream)

    def natural_key(self):
        return (self.uuid,)

    @property
    def is_live(self):
        return self.started_at is not None and self.stopped_at is None


class CreditManager(models.Manager):
    def get_by_natural_key(self, uuid):
        return self.get(uuid=uuid)


class Credit(models.Model):

    uuid = models.UUIDField(
        default=uuid4, unique=True, editable=False, verbose_name=_("UUID")
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="credits", on_delete=models.CASCADE
    )
    stream = models.ForeignKey(Stream, related_name="credits", on_delete=models.CASCADE)
    amount = models.PositiveIntegerField(default=0)

    objects = CreditManager()

    class Meta:
        unique_together = ("user", "stream")

    def __str__(self):
        return f"{self.user} - {self.stream} - {self.amount}"

    def natural_key(self):
        return (self.uuid,)


class ViewerManager(models.Manager):
    def get_by_natural_key(self, viewer_username, stream_uuid):
        return self.get(viewer__username=viewer_username, stream__uuid=stream_uuid)


class Viewer(models.Model):

    viewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="viewing_streams",
        on_delete=models.CASCADE,
    )
    stream = models.ForeignKey(Stream, related_name="viewers", on_delete=models.CASCADE)
    last_viewed_at = models.DateTimeField(default=timezone.now)

    objects = ViewerManager()

    class Meta:
        unique_together = ("viewer", "stream")

    def __str__(self):
        return f"{self.stream} - {self.viewer}"

    def natural_key(self):
        return (self.viewer.username, self.stream.uuid)


class FeedManager(models.Manager):
    def get_by_natural_key(self, uuid):
        return self.get(uuid=uuid)


class Feed(models.Model):

    TYPE_OTHER = "other"
    TYPE_PLAYBYPLAY = "playbyplay"
    TYPE_SUBTITLES = "subtitles"
    TYPE_CHOICES = (
        (TYPE_OTHER, _("Other")),
        (TYPE_PLAYBYPLAY, _("Play by play")),
        (TYPE_SUBTITLES, _("Subtitles")),
    )

    uuid = models.UUIDField(
        default=uuid4, unique=True, editable=False, verbose_name=_("UUID")
    )
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(default=timezone.now, verbose_name=_("Created"))
    type = models.CharField(max_length=30, default=TYPE_OTHER, choices=TYPE_CHOICES)

    objects = FeedManager()

    def __str__(self):
        return self.name

    def natural_key(self):
        return (self.uuid,)

    @property
    def type_display(self):
        return dict(self.TYPE_CHOICES)[self.type]

    @property
    def manifest_url(self):
        return reverse("feed-manifest", args=(self.uuid,))

    @property
    def webvtt_url(self):
        return reverse("feed-webvtt", args=(self.uuid,))


class FeedItemManager(models.Manager):
    def get_by_natural_key(self, uuid):
        return self.get(uuid=uuid)


class FeedItem(models.Model):

    uuid = models.UUIDField(default=uuid4, unique=True, verbose_name=_("UUID"))
    feed = models.ForeignKey(Feed, related_name="items", on_delete=models.CASCADE)
    starts_at = models.DateTimeField(db_index=True)
    ends_at = models.DateTimeField(db_index=True)
    payload = JSONField(blank=True)

    objects = FeedItemManager()

    class Meta:
        ordering = ("starts_at", "ends_at")

    def __str__(self):
        return f"{self.feed} - {self.starts_at} - {self.ends_at}"

    def natural_key(self):
        return (self.uuid,)


@receiver(post_save, sender=Stream)
def drop_inactive_stream(sender, instance=None, **kwargs):
    if not instance.is_active:
        instance.drop()


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance=None, created=False, **kwargs):
    if created and not kwargs["raw"]:
        Profile.objects.create(user=instance)
