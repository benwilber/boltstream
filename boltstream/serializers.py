from django.contrib.auth import get_user_model
from furl import furl
from rest_framework import serializers

from .fields import UUIDHyperlinkedIdentityField
from .models import Stream

User = get_user_model()


class StreamerSerializer(serializers.ModelSerializer):

    id = serializers.ReadOnlyField(source="uuid")
    url = UUIDHyperlinkedIdentityField(view_name="user-detail")
    web_url = serializers.SerializerMethodField()
    name = serializers.ReadOnlyField(source="__str__")

    class Meta:
        model = User
        fields = ("id", "url", "web_url", "username", "name")

    def get_web_url(self, user):
        return self.context["request"].build_absolute_uri(user.get_absolute_url())


class UserSerializer(StreamerSerializer):

    streams = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "url", "web_url", "username", "name", "streams")

    def get_streams(self, user):
        streams = Stream.objects.live().filter(user=user)
        return StreamSerializer(streams, many=True, context=self.context).data


class StreamSerializer(serializers.ModelSerializer):

    id = serializers.ReadOnlyField(source="uuid")
    url = UUIDHyperlinkedIdentityField(view_name="stream-detail")
    web_url = serializers.SerializerMethodField()
    streamer = StreamerSerializer(source="user", read_only=True)
    title = serializers.ReadOnlyField()
    started_at = serializers.DateTimeField(read_only=True)
    image_url = serializers.SerializerMethodField()
    preview_url = serializers.SerializerMethodField()
    manifest_url = serializers.SerializerMethodField()
    channel_url = serializers.SerializerMethodField()
    viewers = serializers.IntegerField(source="viewers.count", read_only=True)

    class Meta:
        model = Stream
        fields = (
            "id",
            "url",
            "web_url",
            "streamer",
            "title",
            "started_at",
            "image_url",
            "preview_url",
            "manifest_url",
            "channel_url",
            "viewers",
        )

    def get_web_url(self, stream):
        return self.context["request"].build_absolute_uri(stream.get_absolute_url())

    def get_manifest_url(self, stream):
        return self.context["request"].build_absolute_uri(stream.master_manifest_url)

    def get_image_url(self, stream):
        return self.context["request"].build_absolute_uri(stream.image_url)

    def get_preview_url(self, stream):
        return self.context["request"].build_absolute_uri(stream.preview_url)

    def get_channel_url(self, stream):
        url = furl(self.context["request"].build_absolute_uri(stream.channel_url))
        scheme = {"http": "ws", "https": "wss"}[url.scheme]
        return url.set(scheme=scheme).url
