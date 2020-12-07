from django.contrib.auth import get_user_model
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Stream
from .permissions import RtmpSecretRequired
from .serializers import StreamSerializer, UserSerializer

User = get_user_model()


class AuthorizeKeyAccessView(APIView):

    queryset = Stream.objects.live()
    permission_classes = (RtmpSecretRequired, IsAuthenticated)

    @method_decorator(never_cache)
    def get(self, request, **kwargs):
        try:
            stream = self.queryset.get(uuid=kwargs["stream_uuid"])
        except Stream.DoesNotExist:
            return Response(_("Forbidden"), status=status.HTTP_403_FORBIDDEN)
        stream.add_viewer(request.user)
        return Response(_("OK"))


class UserViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = User.objects.live()
    lookup_field = "uuid"
    lookup_url_kwarg = "uuid"
    serializer_class = UserSerializer


class StreamViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = Stream.objects.live()
    lookup_field = "uuid"
    lookup_url_kwarg = "uuid"
    serializer_class = StreamSerializer
